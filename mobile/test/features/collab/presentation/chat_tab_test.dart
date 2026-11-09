import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:mobile/features/collab/domain/organization.dart';
import 'package:mobile/features/collab/presentation/diagram_page.dart';

import '../test_support.dart';

const _chatPath = '/api/orgs/acme/documents/d1/chat';

Map<String, Object?> _message(int id, String author, String content, {bool ai = false}) => {
  'id': id,
  'document_id': 'd1',
  'author': author,
  'author_id': ai ? null : 'u1',
  'is_ai': ai,
  'content': content,
  'created_at': '2026-11-08T17:0$id:00Z',
};

Future<void> _open(WidgetTester tester, FakeServer server, {MemberRole role = MemberRole.editor}) async {
  final controller = await signedInController(server);
  await tester.pumpWidget(MaterialApp(
    home: DiagramPage(controller: controller, organization: organization(role: role), document: documentSummary()),
  ));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('shows the conversation, telling the AI apart from people', (tester) async {
    final server = FakeServer({
      'GET $_chatPath': (r) => jsonResponse([
        _message(1, 'Ana Owner', '@IA hola'),
        _message(2, 'IA', 'Hola equipo', ai: true),
      ]),
    });

    await _open(tester, server);

    expect(find.text('@IA hola'), findsOneWidget);
    expect(find.text('Hola equipo'), findsOneWidget);
    expect(find.text('Ana Owner'), findsOneWidget);
    expect(find.byIcon(Icons.smart_toy_outlined), findsOneWidget);
  });

  testWidgets('an empty chat invites the first message and explains the @IA mention', (tester) async {
    await _open(tester, FakeServer({'GET $_chatPath': (r) => jsonResponse([])}));

    expect(find.text('Todavía no hay mensajes. Escribe el primero.'), findsOneWidget);
    expect(find.textContaining('@IA'), findsWidgets);
  });

  testWidgets('an editor sends a message, the field clears and the conversation reloads', (tester) async {
    var posted = false;
    final server = FakeServer({
      'GET $_chatPath': (r) => jsonResponse(posted ? [_message(1, 'Ana Owner', 'hola equipo')] : []),
      'POST $_chatPath': (r) {
        posted = true;
        return jsonResponse({'message': _message(1, 'Ana Owner', 'hola equipo'), 'reply': null, 'ai_error': null, 'proposal': null}, 201);
      },
    });
    await _open(tester, server);

    await tester.enterText(find.byType(TextField), '  hola equipo  ');
    await tester.pump();
    await tester.tap(find.byTooltip('Enviar'));
    await tester.pumpAndSettle();

    expect(jsonDecode(server.requests('POST', _chatPath).single.body), {'content': 'hola equipo'});
    expect(find.text('hola equipo'), findsOneWidget); // in the list, no longer in the field
    expect(tester.widget<TextField>(find.byType(TextField)).controller!.text, isEmpty);
  });

  testWidgets('a blank message cannot be sent', (tester) async {
    final server = FakeServer({'GET $_chatPath': (r) => jsonResponse([])});
    await _open(tester, server);

    await tester.enterText(find.byType(TextField), '   ');
    await tester.pump();
    await tester.tap(find.byTooltip('Enviar'));
    await tester.pumpAndSettle();

    expect(server.requests('POST', _chatPath), isEmpty);
  });

  testWidgets('a reader can read the chat but is not offered a way to write', (tester) async {
    await _open(
      tester,
      FakeServer({'GET $_chatPath': (r) => jsonResponse([_message(1, 'Ana Owner', 'hola')])}),
      role: MemberRole.viewer,
    );

    expect(find.text('hola'), findsOneWidget);
    expect(find.byType(TextField), findsNothing);
    expect(find.text('Eres lector: puedes ver el chat, pero no escribir.'), findsOneWidget);
  });

  testWidgets('a failed send keeps the text, explains it and is never repeated by itself', (tester) async {
    final server = FakeServer({
      'GET $_chatPath': (r) => jsonResponse([]),
      'POST $_chatPath': (r) => throw http.ClientException('connection dropped'),
    });
    await _open(tester, server);

    await tester.enterText(find.byType(TextField), 'importante');
    await tester.pump();
    await tester.tap(find.byTooltip('Enviar'));
    await tester.pumpAndSettle();

    expect(server.requests('POST', _chatPath).length, 1);
    expect(tester.widget<TextField>(find.byType(TextField)).controller!.text, 'importante');
    expect(find.textContaining('no sabemos si tu mensaje llegó', findRichText: true), findsOneWidget);
  });

  testWidgets('the server refusing the role is explained plainly', (tester) async {
    final server = FakeServer({
      'GET $_chatPath': (r) => jsonResponse([]),
      'POST $_chatPath': (r) => jsonResponse({'detail': 'forbidden'}, 403),
    });
    await _open(tester, server);

    await tester.enterText(find.byType(TextField), 'hola');
    await tester.pump();
    await tester.tap(find.byTooltip('Enviar'));
    await tester.pumpAndSettle();

    expect(find.text('Tu rol no permite hacer esto.'), findsOneWidget);
  });

  testWidgets('when the AI could not answer the person is told how to retry', (tester) async {
    final server = FakeServer({
      'GET $_chatPath': (r) => jsonResponse([_message(1, 'Ana Owner', '@IA ayuda')]),
      'POST $_chatPath': (r) => jsonResponse({
        'message': _message(1, 'Ana Owner', '@IA ayuda'),
        'reply': null,
        'ai_error': 'The AI did not answer in time. Mention it again to retry.',
        'proposal': null,
      }, 201),
    });
    await _open(tester, server);

    await tester.enterText(find.byType(TextField), '@IA ayuda');
    await tester.pump();
    await tester.tap(find.byTooltip('Enviar'));
    await tester.pumpAndSettle();

    expect(find.text('La IA no pudo responder. Menciónala de nuevo para reintentar.'), findsOneWidget);
  });

  testWidgets('when the AI leaves a draft the person is pointed to the proposals tab', (tester) async {
    final server = FakeServer({
      'GET $_chatPath': (r) => jsonResponse([]),
      'POST $_chatPath': (r) => jsonResponse({
        'message': _message(1, 'Ana Owner', '@IA agrega Rol'),
        'reply': _message(2, 'IA', 'Dejé el borrador.', ai: true),
        'ai_error': null,
        'proposal': {'id': 'p1', 'status': 'pending'},
      }, 201),
    });
    await _open(tester, server);

    await tester.enterText(find.byType(TextField), '@IA agrega Rol');
    await tester.pump();
    await tester.tap(find.byTooltip('Enviar'));
    await tester.pumpAndSettle();

    expect(find.text('La IA dejó un borrador. Revísalo en la pestaña Propuestas.'), findsOneWidget);
  });
}

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:mobile/features/collab/domain/organization.dart';
import 'package:mobile/features/collab/presentation/diagram_page.dart';

import '../test_support.dart';

const _base = '/api/orgs/acme/documents/d1';
const _chatPath = '$_base/chat';
const _proposalsPath = '$_base/ai-proposals';

Map<String, Object?> _proposal({
  String id = 'p1',
  String status = 'pending',
  List<Map<String, Object?>>? changes,
}) => {
  'id': id,
  'document_id': 'd1',
  'status': status,
  'prompt': 'Agrega una clase Rol',
  'base_revision': 1,
  'changes': changes ??
      [
        {'ok': true, 'message': "Created class 'Rol'"},
        {'ok': true, 'message': "Added attribute 'nombre' to 'Rol'"},
      ],
  'calls': [],
  'applied_indices': null,
  'requested_by': 'Ana Owner',
  'decided_by': null,
  'created_at': '2026-11-08T17:05:00Z',
  'decided_at': null,
};

Future<FakeServer> _open(
  WidgetTester tester,
  Map<String, Handler> routes, {
  MemberRole role = MemberRole.editor,
}) async {
  final server = FakeServer({'GET $_chatPath': (r) => jsonResponse([]), ...routes});
  final controller = await signedInController(server);
  await tester.pumpWidget(MaterialApp(
    home: DiagramPage(controller: controller, organization: organization(role: role), document: documentSummary()),
  ));
  await tester.pumpAndSettle();
  await tester.tap(find.text('Propuestas'));
  await tester.pumpAndSettle();
  return server;
}

void main() {
  testWidgets('lists the pending drafts with who asked, what for and what each change does', (tester) async {
    await _open(tester, {'GET $_proposalsPath': (r) => jsonResponse([_proposal()])});

    expect(find.text('Agrega una clase Rol'), findsOneWidget);
    expect(find.textContaining('Ana Owner'), findsWidgets);
    expect(find.text("Created class 'Rol'"), findsOneWidget);
    expect(find.text("Added attribute 'nombre' to 'Rol'"), findsOneWidget);
    expect(find.text('Aprobar'), findsOneWidget);
    expect(find.text('Rechazar'), findsOneWidget);
  });

  testWidgets('a decided or stale draft is not offered for a decision', (tester) async {
    await _open(tester, {
      'GET $_proposalsPath': (r) => jsonResponse([
        _proposal(id: 'p1', status: 'stale'),
        _proposal(id: 'p2', status: 'approved'),
      ]),
    });

    expect(find.text('Aprobar'), findsNothing);
    expect(find.text('No hay propuestas pendientes. Lo que proponga la IA aparecerá aquí.'), findsOneWidget);
  });

  testWidgets('approving asks first, applies everything once and refreshes the list', (tester) async {
    var approved = false;
    final server = await _open(tester, {
      'GET $_proposalsPath': (r) => jsonResponse(approved ? [] : [_proposal()]),
      'POST $_proposalsPath/p1/approve': (r) {
        approved = true;
        return jsonResponse({..._proposal(status: 'approved'), 'applied_indices': [0, 1]});
      },
    });

    await tester.tap(find.text('Aprobar'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Se aplicarán 2 cambios al diagrama'), findsOneWidget);
    expect(server.requests('POST', '$_proposalsPath/p1/approve'), isEmpty); // nothing before confirming

    await tester.tap(find.text('Aprobar').last);
    await tester.pumpAndSettle();

    final posts = server.requests('POST', '$_proposalsPath/p1/approve').toList();
    expect(posts.length, 1);
    expect(posts.single.body, isEmpty); // no selection: approve every change
    expect(find.text('Propuesta aprobada: se aplicaron 2 cambios.'), findsOneWidget);
    expect(find.text('Agrega una clase Rol'), findsNothing);
  });

  testWidgets('cancelling the confirmation sends nothing', (tester) async {
    final server = await _open(tester, {'GET $_proposalsPath': (r) => jsonResponse([_proposal()])});

    await tester.tap(find.text('Aprobar'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Cancelar'));
    await tester.pumpAndSettle();

    expect(server.requests('POST', '$_proposalsPath/p1/approve'), isEmpty);
    expect(find.text('Agrega una clase Rol'), findsOneWidget);
  });

  testWidgets('rejecting asks first, sends one request and refreshes the list', (tester) async {
    var rejected = false;
    final server = await _open(tester, {
      'GET $_proposalsPath': (r) => jsonResponse(rejected ? [] : [_proposal()]),
      'POST $_proposalsPath/p1/reject': (r) {
        rejected = true;
        return jsonResponse(_proposal(status: 'rejected'));
      },
    });

    await tester.tap(find.text('Rechazar'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Rechazar').last);
    await tester.pumpAndSettle();

    expect(server.requests('POST', '$_proposalsPath/p1/reject').length, 1);
    expect(find.text('Propuesta rechazada.'), findsOneWidget);
    expect(find.text('Agrega una clase Rol'), findsNothing);
  });

  testWidgets('a reader sees the drafts but has no way to decide them', (tester) async {
    await _open(tester, {'GET $_proposalsPath': (r) => jsonResponse([_proposal()])}, role: MemberRole.viewer);

    expect(find.text('Agrega una clase Rol'), findsOneWidget);
    expect(find.text('Aprobar'), findsNothing);
    expect(find.text('Rechazar'), findsNothing);
    expect(find.text('Eres lector: puedes ver las propuestas, pero no decidirlas.'), findsOneWidget);
  });

  testWidgets('a draft with a change that cannot be applied can only be rejected', (tester) async {
    await _open(tester, {
      'GET $_proposalsPath': (r) => jsonResponse([
        _proposal(changes: [
          {'ok': true, 'message': "Created class 'Rol'"},
          {'ok': false, 'message': "Class 'X' does not exist"},
        ]),
      ]),
    });

    expect(find.text('Aprobar'), findsNothing);
    expect(find.text('Rechazar'), findsOneWidget);
    expect(find.text('Alguno de los cambios no se puede aplicar, así que solo puedes rechazar esta propuesta.'), findsOneWidget);
  });

  testWidgets('a draft that went stale under the person is explained in Spanish and the list is refreshed', (tester) async {
    var stale = false;
    await _open(tester, {
      'GET $_proposalsPath': (r) => jsonResponse(stale ? [] : [_proposal()]),
      'POST $_proposalsPath/p1/approve': (r) {
        stale = true;
        return jsonResponse({'detail': 'The diagram changed after this proposal was made. Ask the AI again.'}, 409);
      },
    });

    await tester.tap(find.text('Aprobar'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Aprobar').last);
    await tester.pumpAndSettle();

    expect(find.text('La propuesta ya no es válida: el diagrama cambió o alguien ya decidió. Se actualizó la lista.'), findsOneWidget);
    expect(find.text('Agrega una clase Rol'), findsNothing);
  });

  testWidgets('losing the connection mid-approval is never retried and tells the person to check first', (tester) async {
    final server = await _open(tester, {
      'GET $_proposalsPath': (r) => jsonResponse([_proposal()]),
      'POST $_proposalsPath/p1/approve': (r) => throw http.ClientException('dropped'),
    });

    await tester.tap(find.text('Aprobar'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Aprobar').last);
    await tester.pumpAndSettle();

    expect(server.requests('POST', '$_proposalsPath/p1/approve').length, 1);
    expect(find.textContaining('no sabemos si se aplicó'), findsOneWidget);
    expect(find.text('Agrega una clase Rol'), findsOneWidget);
  });

  testWidgets('the role being refused by the server is explained plainly', (tester) async {
    await _open(tester, {
      'GET $_proposalsPath': (r) => jsonResponse([_proposal()]),
      'POST $_proposalsPath/p1/reject': (r) => jsonResponse({'detail': 'forbidden'}, 403),
    });

    await tester.tap(find.text('Rechazar'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Rechazar').last);
    await tester.pumpAndSettle();

    expect(find.text('Tu rol no permite hacer esto.'), findsOneWidget);
  });

  testWidgets('the diagram has four tabs: chat, proposals, changes and a read-only preview', (tester) async {
    await _open(tester, {'GET $_proposalsPath': (r) => jsonResponse([])});

    expect(find.text('Chat'), findsOneWidget);
    expect(find.text('Propuestas'), findsOneWidget);
    expect(find.text('Cambios'), findsOneWidget);
    expect(find.text('Diagrama'), findsOneWidget);
  });
}

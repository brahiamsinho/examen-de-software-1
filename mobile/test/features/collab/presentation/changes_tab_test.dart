import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/collab/presentation/diagram_page.dart';

import '../test_support.dart';

const _logPath = '/api/orgs/acme/documents/d1/log';
const _chatPath = '/api/orgs/acme/documents/d1/chat';

Map<String, Object?> _entry(int id, String kind, String author, String summary, {bool ai = false}) => {
  'id': id,
  'session': 1,
  'kind': kind,
  'author': author,
  'author_id': ai ? null : 'u1',
  'is_ai': ai,
  'summary': summary,
  'data': {},
  'created_at': '2026-11-08T17:0$id:00Z',
};

Future<void> _openChanges(WidgetTester tester, FakeServer server) async {
  final controller = await signedInController(server);
  await tester.pumpWidget(MaterialApp(
    home: DiagramPage(controller: controller, organization: organization(), document: documentSummary()),
  ));
  await tester.pumpAndSettle();
  await tester.tap(find.text('Cambios'));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('lists what happened in the diagram, newest first, with readable kinds', (tester) async {
    final server = FakeServer({
      'GET $_chatPath': (r) => jsonResponse([]),
      'GET $_logPath': (r) => jsonResponse([
        _entry(1, 'proposal.created', 'IA', 'Propuso 6 cambios, a petición de Ana Owner', ai: true),
        _entry(2, 'change', 'Ana Owner', 'Agregó la clase «Persona»'),
        _entry(3, 'proposal.approved', 'Ana Owner', 'Aprobó la propuesta de la IA (6 de 6 cambios)'),
      ]),
    });

    await _openChanges(tester, server);

    expect(find.text('Propuesta de la IA'), findsOneWidget);
    expect(find.text('Cambio'), findsOneWidget);
    expect(find.text('Aprobada'), findsOneWidget);
    expect(find.text('Agregó la clase «Persona»'), findsOneWidget);
    final newest = tester.getTopLeft(find.text('Aprobó la propuesta de la IA (6 de 6 cambios)')).dy;
    final oldest = tester.getTopLeft(find.text('Propuso 6 cambios, a petición de Ana Owner')).dy;
    expect(newest, lessThan(oldest));
  });

  testWidgets('asks only for the latest entries', (tester) async {
    final server = FakeServer({
      'GET $_chatPath': (r) => jsonResponse([]),
      'GET $_logPath': (r) => jsonResponse([]),
    });

    await _openChanges(tester, server);

    expect(server.requests('GET', _logPath).single.url.queryParameters['limit'], '100');
  });

  testWidgets('an unknown kind from a newer backend still shows, never crashes', (tester) async {
    final server = FakeServer({
      'GET $_chatPath': (r) => jsonResponse([]),
      'GET $_logPath': (r) => jsonResponse([_entry(1, 'something.new', 'Ana', 'Hizo algo nuevo')]),
    });

    await _openChanges(tester, server);

    expect(find.text('Hizo algo nuevo'), findsOneWidget);
    expect(find.text('Otro'), findsOneWidget);
  });

  testWidgets('a diagram with no history says so', (tester) async {
    final server = FakeServer({
      'GET $_chatPath': (r) => jsonResponse([]),
      'GET $_logPath': (r) => jsonResponse([]),
    });

    await _openChanges(tester, server);

    expect(find.text('Todavía no hay cambios registrados en este diagrama.'), findsOneWidget);
  });
}

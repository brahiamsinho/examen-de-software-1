import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/collab/presentation/diagram_page.dart';

import '../test_support.dart';

const _docPath = '/api/orgs/acme/documents/d1';

Map<String, Object?> _klass(
  String id,
  String name, {
  List<Map<String, Object?>> attributes = const [],
  bool abstract = false,
}) => {
  'id': id,
  'name': name,
  'attributes': attributes,
  'operations': [],
  'is_abstract': abstract,
};

Map<String, Object?> _document({List<Map<String, Object?>> classes = const [], List<Map<String, Object?>> relationships = const []}) => {
  'id': 'd1',
  'revision': 3,
  'metadata': {'name': 'Ventas', 'description': ''},
  'model': {'classes': classes, 'enumerations': [], 'relationships': relationships},
  'layout': {'positions': {}},
};

Future<void> _openPreview(WidgetTester tester, FakeServer server) async {
  final controller = await signedInController(server);
  await tester.pumpWidget(MaterialApp(
    home: DiagramPage(controller: controller, organization: organization(), document: documentSummary()),
  ));
  await tester.pumpAndSettle();
  await tester.tap(find.text('Diagrama'));
  await tester.pumpAndSettle();
}

FakeServer _server(Handler doc) => FakeServer({
  'GET /api/orgs/acme/documents/d1/chat': (r) => jsonResponse([]),
  'GET /api/orgs/acme/documents/d1/ai-proposals': (r) => jsonResponse([]),
  'GET /api/orgs/acme/documents/d1/log': (r) => jsonResponse([]),
  'GET $_docPath': doc,
});

void main() {
  testWidgets('shows each class with its attributes and a count of what the diagram has', (tester) async {
    final server = _server((r) => jsonResponse(_document(
      classes: [
        _klass('c1', 'Persona', attributes: [
          {'id': 'a1', 'name': 'nombre', 'type': 'String', 'visibility': 'public'},
        ]),
        _klass('c2', 'Pedido'),
      ],
      relationships: [
        {
          'id': 'r1',
          'kind': 'association',
          'source': {'class_id': 'c1', 'multiplicity': {'lower': 1, 'upper': 1}, 'role': null},
          'target': {'class_id': 'c2', 'multiplicity': {'lower': 0, 'upper': null}, 'role': null},
          'name': '',
        },
      ],
    )));

    await _openPreview(tester, server);

    expect(find.text('Persona'), findsOneWidget);
    expect(find.text('Pedido'), findsOneWidget);
    expect(find.text('+ nombre: String'), findsOneWidget);
    expect(find.text('2 clases · 1 relación'), findsOneWidget);
    expect(server.requests('GET', _docPath), hasLength(1));
  });

  testWidgets('writes the name of an abstract class in italics, as UML 2.5 asks', (tester) async {
    await _openPreview(
      tester,
      _server((r) => jsonResponse(_document(classes: [_klass('c1', 'Forma', abstract: true), _klass('c2', 'Pedido')]))),
    );

    expect(tester.widget<Text>(find.text('Forma')).style?.fontStyle, FontStyle.italic);
    expect(tester.widget<Text>(find.text('Pedido')).style?.fontStyle, isNot(FontStyle.italic));
  });

  testWidgets('says so when the diagram is still empty', (tester) async {
    await _openPreview(tester, _server((r) => jsonResponse(_document())));

    expect(find.text('El diagrama todavía está vacío.'), findsOneWidget);
  });

  testWidgets('explains a failure and loads again with Reintentar', (tester) async {
    var calls = 0;
    final server = _server((r) {
      calls++;
      return calls == 1 ? jsonResponse({'detail': 'boom'}, 500) : jsonResponse(_document(classes: [_klass('c1', 'Persona')]));
    });

    await _openPreview(tester, server);
    expect(find.text('Reintentar'), findsOneWidget);

    await tester.tap(find.text('Reintentar'));
    await tester.pumpAndSettle();

    expect(find.text('Persona'), findsOneWidget);
  });

  testWidgets('the refresh button asks the server for the diagram again', (tester) async {
    final server = _server((r) => jsonResponse(_document(classes: [_klass('c1', 'Persona')])));
    await _openPreview(tester, server);

    await tester.tap(find.byTooltip('Actualizar'));
    await tester.pumpAndSettle();

    expect(server.requests('GET', _docPath), hasLength(2));
  });
}

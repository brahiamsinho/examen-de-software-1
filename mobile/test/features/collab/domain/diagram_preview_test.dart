import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/collab/domain/diagram_preview.dart';

Map<String, Object?> _document() => {
  'id': 'd1',
  'revision': 7,
  'metadata': {'name': 'Ventas', 'description': ''},
  'model': {
    'classes': [
      {
        'id': 'c1',
        'name': 'Pedido',
        'attributes': [
          {'id': 'a1', 'name': 'total', 'type': 'Decimal', 'visibility': 'private'},
          {
            'id': 'a2',
            'name': 'estado',
            'type': {
              'enumeration_ref': {'enumeration_id': 'e1'},
            },
            'visibility': 'public',
          },
        ],
        'operations': [
          {'id': 'o1', 'name': 'cancelar', 'return_type': null, 'parameters': [], 'visibility': 'public'},
          {
            'id': 'o2',
            'name': 'agregar',
            'return_type': 'Integer',
            'parameters': [
              {'name': 'cantidad', 'type': 'Integer'},
            ],
            'visibility': 'protected',
          },
        ],
      },
      {'id': 'c2', 'name': 'Cliente', 'attributes': [], 'operations': []},
    ],
    'enumerations': [
      {'id': 'e1', 'name': 'EstadoPedido', 'literals': []},
    ],
    'relationships': [
      {
        'id': 'r1',
        'kind': 'composition',
        'source': {
          'class_id': 'c2',
          'multiplicity': {'lower': 1, 'upper': 1},
          'role': null,
        },
        'target': {
          'class_id': 'c1',
          'multiplicity': {'lower': 0, 'upper': null},
          'role': null,
        },
        'name': 'realiza',
      },
    ],
  },
  'layout': {
    'positions': {
      'c1': {'x': 300.0, 'y': 120.0},
    },
  },
};

void main() {
  test('reads the classes with readable members, an enumeration type by its name', () {
    final preview = DiagramPreview.fromJson(_document());

    expect(preview.name, 'Ventas');
    expect(preview.revision, 7);
    final pedido = preview.classes.first;
    expect(pedido.name, 'Pedido');
    expect(pedido.attributes, ['- total: Decimal', '+ estado: EstadoPedido']);
    expect(pedido.operations, ['+ cancelar()', '# agregar(cantidad: Integer): Integer']);
    expect(preview.classes.last.attributes, isEmpty);
  });

  test('reads the relationships with their multiplicities, where * means no upper bound', () {
    final relationship = DiagramPreview.fromJson(_document()).relationships.single;

    expect(relationship.kind, RelationshipKind.composition);
    expect(relationship.sourceId, 'c2');
    expect(relationship.targetId, 'c1');
    expect(relationship.sourceMultiplicity, '1');
    expect(relationship.targetMultiplicity, '0..*');
  });

  test('keeps the saved position of a class and leaves the others without one', () {
    final preview = DiagramPreview.fromJson(_document());

    expect(preview.classes.first.x, 300.0);
    expect(preview.classes.first.y, 120.0);
    expect(preview.classes.last.x, isNull);
  });

  test('reads whether a class is abstract, and treats a diagram saved before the flag as concrete', () {
    final json = _document();
    ((json['model'] as Map)['classes'] as List).first['is_abstract'] = true;

    final classes = DiagramPreview.fromJson(json).classes;

    expect(classes.first.isAbstract, isTrue);
    expect(classes.last.isAbstract, isFalse); // no key at all
  });

  test('reads a dependency, which UML 2.5 defines without multiplicities', () {
    final json = _document();
    ((json['model'] as Map)['relationships'] as List).first['kind'] = 'dependency';

    final relationship = DiagramPreview.fromJson(json).relationships.single;

    expect(relationship.kind, RelationshipKind.dependency);
    expect(RelationshipKind.dependency.hasMultiplicity, isFalse);
  });

  test('only generalization and dependency go without multiplicities', () {
    expect(
      {for (final kind in RelationshipKind.values) kind: kind.hasMultiplicity},
      {
        RelationshipKind.association: true,
        RelationshipKind.aggregation: true,
        RelationshipKind.composition: true,
        RelationshipKind.generalization: false,
        RelationshipKind.dependency: false,
      },
    );
  });

  test('an unknown relationship kind still reads, as a plain association', () {
    final json = _document();
    ((json['model'] as Map)['relationships'] as List).first['kind'] = 'something-new';

    expect(DiagramPreview.fromJson(json).relationships.single.kind, RelationshipKind.association);
  });

  test('a relationship pointing to a class that is gone is dropped instead of crashing', () {
    final json = _document();
    (((json['model'] as Map)['relationships'] as List).first['target'] as Map)['class_id'] = 'missing';

    expect(DiagramPreview.fromJson(json).relationships, isEmpty);
  });
}

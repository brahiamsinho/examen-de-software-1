/// A read-only picture of a diagram for the phone (GitHub #19): just enough to
/// draw it, parsed from the server's document (`model` + `layout`). Nothing here
/// edits anything.
enum RelationshipKind {
  association,
  aggregation,
  composition,
  generalization,
  dependency;

  /// UML 2.5 defines no multiplicity for these two; the server keeps a neutral 1..1
  /// on their ends, which must never be drawn.
  bool get hasMultiplicity => this != generalization && this != dependency;
}

class PreviewClass {
  const PreviewClass({
    required this.id,
    required this.name,
    required this.attributes,
    required this.operations,
    this.isAbstract = false,
    this.x,
    this.y,
  });

  final String id;
  final String name;

  /// Ready to show, e.g. `- total: Decimal`.
  final List<String> attributes;

  /// Ready to show, e.g. `+ cancelar()`.
  final List<String> operations;

  /// UML 2.5 `isAbstract`; its name is written in italics.
  final bool isAbstract;

  /// Where the web canvas put it; null when it has never been placed.
  final double? x;
  final double? y;
}

class PreviewRelationship {
  const PreviewRelationship({
    required this.id,
    required this.kind,
    required this.sourceId,
    required this.targetId,
    required this.sourceMultiplicity,
    required this.targetMultiplicity,
    required this.name,
  });

  final String id;
  final RelationshipKind kind;
  final String sourceId;
  final String targetId;
  final String sourceMultiplicity;
  final String targetMultiplicity;
  final String name;
}

class DiagramPreview {
  const DiagramPreview({
    required this.name,
    required this.revision,
    required this.classes,
    required this.relationships,
  });

  final String name;
  final int revision;
  final List<PreviewClass> classes;
  final List<PreviewRelationship> relationships;

  factory DiagramPreview.fromJson(Map<String, Object?> json) {
    final model = (json['model'] as Map?)?.cast<String, Object?>() ?? const {};
    final positions = ((json['layout'] as Map?)?['positions'] as Map?)?.cast<String, Object?>() ?? const {};

    final enumerationNames = <String, String>{
      for (final item in (model['enumerations'] as List?) ?? const [])
        if (item is Map) '${item['id']}': '${item['name']}',
    };

    final classes = <PreviewClass>[
      for (final item in (model['classes'] as List?) ?? const [])
        if (item is Map) _readClass(item.cast<String, Object?>(), positions, enumerationNames),
    ];
    final known = {for (final item in classes) item.id};

    final relationships = <PreviewRelationship>[
      for (final item in (model['relationships'] as List?) ?? const [])
        if (item is Map) ..._readRelationship(item.cast<String, Object?>(), known),
    ];

    final metadata = (json['metadata'] as Map?)?.cast<String, Object?>() ?? const {};
    return DiagramPreview(
      name: '${metadata['name'] ?? ''}',
      revision: (json['revision'] as num?)?.toInt() ?? 0,
      classes: classes,
      relationships: relationships,
    );
  }
}

PreviewClass _readClass(Map<String, Object?> json, Map<String, Object?> positions, Map<String, String> enumerations) {
  final id = '${json['id']}';
  final position = positions[id];
  final point = position is Map ? position : null;
  return PreviewClass(
    id: id,
    name: '${json['name']}',
    attributes: [
      for (final item in (json['attributes'] as List?) ?? const [])
        if (item is Map)
          '${_visibility(item['visibility'])} ${item['name']}: ${_typeLabel(item['type'], enumerations)}',
    ],
    operations: [
      for (final item in (json['operations'] as List?) ?? const [])
        if (item is Map) _operationLabel(item.cast<String, Object?>(), enumerations),
    ],
    isAbstract: json['is_abstract'] == true,
    x: (point?['x'] as num?)?.toDouble(),
    y: (point?['y'] as num?)?.toDouble(),
  );
}

String _operationLabel(Map<String, Object?> json, Map<String, String> enumerations) {
  final parameters = [
    for (final item in (json['parameters'] as List?) ?? const [])
      if (item is Map) '${item['name']}: ${_typeLabel(item['type'], enumerations)}',
  ].join(', ');
  final returnType = json['return_type'];
  final suffix = returnType == null ? '' : ': ${_typeLabel(returnType, enumerations)}';
  return '${_visibility(json['visibility'])} ${json['name']}($parameters)$suffix';
}

String _visibility(Object? value) => switch (value) {
  'private' => '-',
  'protected' => '#',
  'package' => '~',
  _ => '+',
};

String _typeLabel(Object? type, Map<String, String> enumerations) {
  if (type is Map) {
    final reference = type['enumeration_ref'];
    final id = reference is Map ? '${reference['enumeration_id']}' : '';
    return enumerations[id] ?? '?';
  }
  return '$type';
}

// A relationship whose end points at a class that no longer exists is skipped
// rather than drawn to nowhere (or crashing the screen).
Iterable<PreviewRelationship> _readRelationship(Map<String, Object?> json, Set<String> knownClasses) sync* {
  final source = (json['source'] as Map?)?.cast<String, Object?>() ?? const {};
  final target = (json['target'] as Map?)?.cast<String, Object?>() ?? const {};
  final sourceId = '${source['class_id']}';
  final targetId = '${target['class_id']}';
  if (!knownClasses.contains(sourceId) || !knownClasses.contains(targetId)) return;
  yield PreviewRelationship(
    id: '${json['id']}',
    kind: RelationshipKind.values.firstWhere((kind) => kind.name == json['kind'], orElse: () => RelationshipKind.association),
    sourceId: sourceId,
    targetId: targetId,
    sourceMultiplicity: _multiplicity(source['multiplicity']),
    targetMultiplicity: _multiplicity(target['multiplicity']),
    name: '${json['name'] ?? ''}',
  );
}

String _multiplicity(Object? value) {
  if (value is! Map) return '';
  final lower = value['lower'];
  final upper = value['upper'];
  final top = upper == null ? '*' : '$upper';
  return lower == upper ? '$lower' : '$lower..$top';
}

/// What a placed button does when the screen runs (spec: four CRUD actions
/// per the proposed MVP — list/create act on the group's collection
/// endpoint directly; update/delete additionally ask for a record id, since
/// there is no data grid yet to pick one from).
enum ScreenAction { list, create, update, delete }

/// One widget placed on the designer canvas. Immutable — every edit
/// (reposition, rebind, retype) replaces the instance via [copyWith], the
/// same pattern the rest of this app's domain models use.
sealed class ScreenWidgetConfig {
  const ScreenWidgetConfig({required this.id, required this.x, required this.y});

  final String id;
  final double x;
  final double y;

  ScreenWidgetConfig copyWith({double? x, double? y});

  Map<String, Object?> toJson();

  static ScreenWidgetConfig fromJson(Map<String, Object?> json) {
    final id = json['id'] as String;
    final x = (json['x'] as num).toDouble();
    final y = (json['y'] as num).toDouble();
    switch (json['type']) {
      case 'label':
        return LabelWidgetConfig(id: id, x: x, y: y, text: json['text'] as String? ?? 'Label');
      case 'field':
        return FieldWidgetConfig(id: id, x: x, y: y, fieldName: json['fieldName'] as String? ?? '');
      case 'button':
        return ButtonWidgetConfig(
          id: id,
          x: x,
          y: y,
          action: ScreenAction.values.byName(json['action'] as String? ?? 'list'),
        );
      default:
        throw FormatException('Unknown widget type: ${json['type']}');
    }
  }
}

/// Static text, e.g. a title or a hint.
class LabelWidgetConfig extends ScreenWidgetConfig {
  const LabelWidgetConfig({required super.id, required super.x, required super.y, required this.text});

  final String text;

  @override
  LabelWidgetConfig copyWith({double? x, double? y, String? text}) =>
      LabelWidgetConfig(id: id, x: x ?? this.x, y: y ?? this.y, text: text ?? this.text);

  @override
  Map<String, Object?> toJson() => {'type': 'label', 'id': id, 'x': x, 'y': y, 'text': text};
}

/// A text input bound to one attribute of the connected class, e.g. `edad`.
/// Its typed value feeds `create`/`update` request bodies at run time.
class FieldWidgetConfig extends ScreenWidgetConfig {
  const FieldWidgetConfig({required super.id, required super.x, required super.y, required this.fieldName});

  final String fieldName;

  @override
  FieldWidgetConfig copyWith({double? x, double? y, String? fieldName}) =>
      FieldWidgetConfig(id: id, x: x ?? this.x, y: y ?? this.y, fieldName: fieldName ?? this.fieldName);

  @override
  Map<String, Object?> toJson() => {'type': 'field', 'id': id, 'x': x, 'y': y, 'fieldName': fieldName};
}

/// Triggers one CRUD action against the connected class's endpoints.
class ButtonWidgetConfig extends ScreenWidgetConfig {
  const ButtonWidgetConfig({required super.id, required super.x, required super.y, required this.action});

  final ScreenAction action;

  @override
  ButtonWidgetConfig copyWith({double? x, double? y, ScreenAction? action}) =>
      ButtonWidgetConfig(id: id, x: x ?? this.x, y: y ?? this.y, action: action ?? this.action);

  @override
  Map<String, Object?> toJson() => {'type': 'button', 'id': id, 'x': x, 'y': y, 'action': action.name};
}

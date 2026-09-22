import 'screen_widget_config.dart';

/// A saved screen design: a user-named screen (not tied to any single
/// class — each [FieldWidgetConfig]/[ButtonWidgetConfig] carries its own
/// `groupName`, so one screen can mix widgets from several classes).
/// Round-trips through JSON so it can be stored locally
/// (data/screen_layout_store.dart) and reloaded on the next visit.
class ScreenLayout {
  const ScreenLayout({required this.name, required this.widgets});

  final String name;
  final List<ScreenWidgetConfig> widgets;

  factory ScreenLayout.empty(String name) => ScreenLayout(name: name, widgets: const []);

  ScreenLayout withWidgets(List<ScreenWidgetConfig> widgets) => ScreenLayout(name: name, widgets: widgets);

  Map<String, Object?> toJson() => {
    'name': name,
    'widgets': [for (final widget in widgets) widget.toJson()],
  };

  factory ScreenLayout.fromJson(Map<String, Object?> json) => ScreenLayout(
    name: json['name'] as String,
    widgets: [
      for (final raw in (json['widgets'] as List<Object?>))
        ScreenWidgetConfig.fromJson(raw as Map<String, Object?>),
    ],
  );
}

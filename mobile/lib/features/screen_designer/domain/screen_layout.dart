import 'screen_widget_config.dart';

/// A saved screen design: every widget the user placed for one endpoint
/// group (e.g. `class-a-controller`). Round-trips through JSON so it can be
/// stored locally (data/screen_layout_store.dart) and reloaded on the next
/// visit to the same group.
class ScreenLayout {
  const ScreenLayout({required this.groupName, required this.widgets});

  final String groupName;
  final List<ScreenWidgetConfig> widgets;

  factory ScreenLayout.empty(String groupName) => ScreenLayout(groupName: groupName, widgets: const []);

  ScreenLayout withWidgets(List<ScreenWidgetConfig> widgets) => ScreenLayout(groupName: groupName, widgets: widgets);

  Map<String, Object?> toJson() => {
    'groupName': groupName,
    'widgets': [for (final widget in widgets) widget.toJson()],
  };

  factory ScreenLayout.fromJson(Map<String, Object?> json) => ScreenLayout(
    groupName: json['groupName'] as String,
    widgets: [
      for (final raw in (json['widgets'] as List<Object?>))
        ScreenWidgetConfig.fromJson(raw as Map<String, Object?>),
    ],
  );
}

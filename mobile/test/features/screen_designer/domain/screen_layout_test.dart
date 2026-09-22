import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/screen_designer/domain/screen_layout.dart';
import 'package:mobile/features/screen_designer/domain/screen_widget_config.dart';

void main() {
  group('ScreenLayout JSON round trip', () {
    test('every widget kind survives toJson -> fromJson', () {
      final layout = ScreenLayout(
        groupName: 'class-a-controller',
        widgets: const [
          LabelWidgetConfig(id: 'w1', x: 10, y: 20, text: 'Class A'),
          FieldWidgetConfig(id: 'w2', x: 10, y: 60, fieldName: 'edad'),
          ButtonWidgetConfig(id: 'w3', x: 10, y: 100, action: ScreenAction.create),
        ],
      );

      final restored = ScreenLayout.fromJson(layout.toJson());

      expect(restored.groupName, 'class-a-controller');
      expect(restored.widgets, hasLength(3));
      expect((restored.widgets[0] as LabelWidgetConfig).text, 'Class A');
      expect((restored.widgets[1] as FieldWidgetConfig).fieldName, 'edad');
      expect((restored.widgets[2] as ButtonWidgetConfig).action, ScreenAction.create);
      expect(restored.widgets[1].x, 10);
      expect(restored.widgets[2].y, 100);
    });

    test('an empty layout round trips to no widgets', () {
      final restored = ScreenLayout.fromJson(ScreenLayout.empty('orders').toJson());

      expect(restored.groupName, 'orders');
      expect(restored.widgets, isEmpty);
    });
  });

  group('ScreenWidgetConfig.copyWith', () {
    test('repositions without touching the binding', () {
      const field = FieldWidgetConfig(id: 'w1', x: 0, y: 0, fieldName: 'name');

      final moved = field.copyWith(x: 42, y: 99);

      expect(moved.x, 42);
      expect(moved.y, 99);
      expect(moved.fieldName, 'name');
    });
  });
}

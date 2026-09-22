import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/screen_designer/data/screen_layout_store.dart';
import 'package:mobile/features/screen_designer/domain/screen_layout.dart';
import 'package:mobile/features/screen_designer/domain/screen_widget_config.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('ScreenLayoutStore', () {
    test('a group with nothing saved yet loads null', () async {
      final loaded = await const ScreenLayoutStore().load('orders');

      expect(loaded, isNull);
    });

    test('save then load returns an equivalent layout, keyed by group name', () async {
      const store = ScreenLayoutStore();
      final layout = ScreenLayout(
        groupName: 'class-a-controller',
        widgets: const [LabelWidgetConfig(id: 'w1', x: 5, y: 5, text: 'Class A')],
      );

      await store.save(layout);
      final loaded = await store.load('class-a-controller');
      final otherGroup = await store.load('class-b-controller');

      expect(loaded!.widgets, hasLength(1));
      expect((loaded.widgets.single as LabelWidgetConfig).text, 'Class A');
      expect(otherGroup, isNull);
    });
  });
}

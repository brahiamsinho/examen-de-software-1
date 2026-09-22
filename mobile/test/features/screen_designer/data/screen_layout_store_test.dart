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
    test('a screen with nothing saved yet loads null, and starts with an empty index', () async {
      const store = ScreenLayoutStore();

      expect(await store.load('Orders'), isNull);
      expect(await store.listNames(), isEmpty);
    });

    test('save then load returns an equivalent layout, keyed by screen name, and lists it', () async {
      const store = ScreenLayoutStore();
      final layout = ScreenLayout(
        name: 'My screen',
        widgets: const [LabelWidgetConfig(id: 'w1', x: 5, y: 5, text: 'Class A')],
      );

      await store.save(layout);
      final loaded = await store.load('My screen');
      final missing = await store.load('Some other screen');

      expect(loaded!.widgets, hasLength(1));
      expect((loaded.widgets.single as LabelWidgetConfig).text, 'Class A');
      expect(missing, isNull);
      expect(await store.listNames(), ['My screen']);
    });

    test('saving twice under the same name overwrites it without duplicating the index', () async {
      const store = ScreenLayoutStore();
      await store.save(ScreenLayout.empty('My screen'));
      await store.save(
        ScreenLayout(
          name: 'My screen',
          widgets: const [LabelWidgetConfig(id: 'w1', x: 0, y: 0, text: 'v2')],
        ),
      );

      expect(await store.listNames(), ['My screen']);
      expect((await store.load('My screen'))!.widgets, hasLength(1));
    });

    test('delete removes the layout and drops it from the index', () async {
      const store = ScreenLayoutStore();
      await store.save(ScreenLayout.empty('My screen'));

      await store.delete('My screen');

      expect(await store.load('My screen'), isNull);
      expect(await store.listNames(), isEmpty);
    });
  });
}

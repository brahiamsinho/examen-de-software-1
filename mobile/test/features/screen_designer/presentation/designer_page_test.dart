import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/api_connection/domain/api_discovery.dart';
import 'package:mobile/features/screen_designer/data/screen_layout_store.dart';
import 'package:mobile/features/screen_designer/domain/screen_layout.dart';
import 'package:mobile/features/screen_designer/domain/screen_widget_config.dart';
import 'package:mobile/features/screen_designer/presentation/designer_page.dart';
import 'package:mobile/features/screen_designer/presentation/runtime_screen_page.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _classA = EndpointGroup(
  name: 'class-a-controller',
  endpoints: [
    ApiEndpoint(method: 'GET', path: '/api/class-as'),
    ApiEndpoint(method: 'POST', path: '/api/class-as'),
  ],
);
const _classB = EndpointGroup(
  name: 'class-b-controller',
  endpoints: [
    ApiEndpoint(method: 'GET', path: '/api/class-bs'),
    ApiEndpoint(method: 'POST', path: '/api/class-bs'),
  ],
);
const _classAWithAttributes = EndpointGroup(
  name: 'class-a-controller',
  endpoints: [
    ApiEndpoint(method: 'GET', path: '/api/class-as'),
    ApiEndpoint(method: 'POST', path: '/api/class-as'),
  ],
  attributeNames: ['edad', 'name'],
);

Future<void> _pump(WidgetTester tester, {List<EndpointGroup> groups = const [_classA]}) => tester.pumpWidget(
  MaterialApp(
    home: ScreenDesignerPage(name: 'My screen', groups: groups, deploymentBase: Uri.parse('http://h/gen/abc/')),
  ),
);

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('ScreenDesignerPage, one class available', () {
    testWidgets('tapping "Label" in the palette places one on the canvas without asking which class', (tester) async {
      await _pump(tester);
      await tester.pumpAndSettle();

      await tester.tap(find.widgetWithText(ActionChip, 'Label'));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(FilledButton, 'Save')); // confirm the add-label dialog
      await tester.pumpAndSettle();

      expect(find.text('Label'), findsWidgets); // the palette chip AND the placed widget's default text
      expect(find.text('Class'), findsNothing); // no class picker with only one group
    });

    testWidgets('dragging a placed widget moves it, and the new position is what gets saved', (tester) async {
      await _pump(tester);
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(ActionChip, 'Label'));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(FilledButton, 'Save')); // add-label dialog
      await tester.pumpAndSettle();

      final placed = find.descendant(of: find.byKey(const Key('designer-canvas')), matching: find.byType(Card));

      // Several small moves (not one big jump) read unambiguously as a pan
      // against this same detector's competing `onTap`, like a real touch.
      final gesture = await tester.startGesture(tester.getCenter(placed));
      for (var i = 0; i < 4; i++) {
        await gesture.moveBy(const Offset(10, 7.5));
        await tester.pump(const Duration(milliseconds: 16));
      }
      await gesture.up();
      await tester.pumpAndSettle();

      await tester.tap(find.byTooltip('Save'));
      await tester.pumpAndSettle();

      final saved = (await const ScreenLayoutStore().load('My screen'))!.widgets.single;
      // The exact total depends on how the test harness delivers the
      // simulated pointer events; what matters is that it moved, clearly
      // and in the requested direction, not the touch-slop-sensitive exact
      // pixel count.
      expect(saved.x, greaterThan(16));
      expect(saved.y, greaterThan(16));
    });

    testWidgets('Save persists the layout, reloaded by a fresh instance for the same screen name', (tester) async {
      await _pump(tester);
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(ActionChip, 'Label'));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(FilledButton, 'Save')); // add-label dialog
      await tester.pumpAndSettle();

      await tester.tap(find.byTooltip('Save'));
      await tester.pumpAndSettle();

      final loaded = await const ScreenLayoutStore().load('My screen');
      expect(loaded, isNotNull);
      expect(loaded!.widgets, hasLength(1));
      expect(loaded.widgets.single, isA<LabelWidgetConfig>());
    });

    testWidgets('a saved layout loads back into the canvas', (tester) async {
      await const ScreenLayoutStore().save(
        ScreenLayout(
          name: 'My screen',
          widgets: const [LabelWidgetConfig(id: 'w1', x: 12, y: 12, text: 'Preloaded')],
        ),
      );

      await _pump(tester);
      await tester.pumpAndSettle();

      expect(find.text('Preloaded'), findsOneWidget);
    });

    testWidgets('Preview opens the runtime screen once something is placed', (tester) async {
      await _pump(tester);
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(ActionChip, 'Label'));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(FilledButton, 'Save'));
      await tester.pumpAndSettle();

      await tester.tap(find.byTooltip('Preview'));
      await tester.pumpAndSettle();

      expect(find.byType(RuntimeScreenPage), findsOneWidget);
    });
  });

  group('ScreenDesignerPage, several classes available', () {
    testWidgets('adding a field asks which class it binds to, and the chip shows it', (tester) async {
      await _pump(tester, groups: const [_classA, _classB]);
      await tester.pumpAndSettle();

      await tester.tap(find.widgetWithText(ActionChip, 'Field'));
      await tester.pumpAndSettle();
      expect(find.text('Class'), findsOneWidget); // the class picker, since there are 2 groups

      await tester.tap(find.text('class-b-controller'));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField), 'name');
      await tester.tap(find.widgetWithText(FilledButton, 'Save')); // confirm the add-field dialog
      await tester.pumpAndSettle();

      expect(find.textContaining('class-b-controller'), findsWidgets);

      await tester.tap(find.byTooltip('Save')); // persist the whole screen
      await tester.pumpAndSettle();

      final saved = (await const ScreenLayoutStore().load('My screen'))!.widgets.single as FieldWidgetConfig;
      expect(saved.groupName, 'class-b-controller');
      expect(saved.fieldName, 'name');
    });

    testWidgets('a class with known attributes offers a picker instead of free text', (tester) async {
      await _pump(tester, groups: const [_classAWithAttributes, _classB]);
      await tester.pumpAndSettle();

      await tester.tap(find.widgetWithText(ActionChip, 'Field'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('class-a-controller'));
      await tester.pumpAndSettle();

      expect(find.text('Attribute'), findsOneWidget); // the attribute picker, not "Add field"
      expect(find.text('edad'), findsOneWidget);
      expect(find.text('name'), findsOneWidget);

      await tester.tap(find.text('edad'));
      await tester.pumpAndSettle();

      expect(find.textContaining('Field: edad'), findsWidgets);
    });
  });
}

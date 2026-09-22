import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/api_connection/domain/api_discovery.dart';
import 'package:mobile/features/api_connection/presentation/discovery_page.dart';
import 'package:mobile/features/screen_designer/data/screen_layout_store.dart';
import 'package:mobile/features/screen_designer/domain/screen_layout.dart';
import 'package:mobile/features/screen_designer/presentation/designer_page.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _discovery = ApiDiscovery(
  title: 'Demo API',
  version: '1.0',
  openApiVersion: '3.1.0',
  groups: [
    EndpointGroup(
      name: 'thing-controller',
      endpoints: [ApiEndpoint(method: 'GET', path: '/api/things')],
    ),
  ],
);

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('tapping a group name suggests it as the new screen\'s name, then opens the designer', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: DiscoveryPage(
          discovery: _discovery,
          openApiUri: Uri.parse('http://h/gen/abc/v3/api-docs'),
        ),
      ),
    );

    await tester.tap(find.text('thing-controller'));
    await tester.pumpAndSettle();

    expect(find.text('New screen'), findsOneWidget);
    expect(tester.widget<TextField>(find.byType(TextField)).controller!.text, 'thing-controller');

    await tester.tap(find.widgetWithText(FilledButton, 'Create'));
    await tester.pumpAndSettle();

    expect(find.byType(ScreenDesignerPage), findsOneWidget);
    expect(find.text('Design: thing-controller'), findsOneWidget);
  });

  testWidgets('the folder icon lists saved screens and reopens the chosen one', (tester) async {
    await const ScreenLayoutStore().save(ScreenLayout.empty('My mixed screen'));

    await tester.pumpWidget(
      MaterialApp(
        home: DiscoveryPage(
          discovery: _discovery,
          openApiUri: Uri.parse('http://h/gen/abc/v3/api-docs'),
        ),
      ),
    );

    await tester.tap(find.byTooltip('Open a saved screen'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('My mixed screen'));
    await tester.pumpAndSettle();

    expect(find.text('Design: My mixed screen'), findsOneWidget);
  });
}

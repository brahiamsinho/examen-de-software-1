import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/api_connection/domain/api_discovery.dart';
import 'package:mobile/features/api_connection/presentation/discovery_page.dart';
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

  testWidgets('tapping a group name opens the screen designer for it', (tester) async {
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

    expect(find.byType(ScreenDesignerPage), findsOneWidget);
    expect(find.text('Design: thing-controller'), findsOneWidget);
  });
}

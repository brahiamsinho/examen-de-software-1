import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/features/api_connection/domain/api_discovery.dart';
import 'package:mobile/features/screen_designer/data/screen_action_client.dart';
import 'package:mobile/features/screen_designer/domain/screen_layout.dart';
import 'package:mobile/features/screen_designer/domain/screen_widget_config.dart';
import 'package:mobile/features/screen_designer/presentation/runtime_screen_page.dart';

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

Future<void> _pump(
  WidgetTester tester, {
  required List<Object> widgets,
  List<EndpointGroup> groups = const [_classA],
  required Future<http.Response> Function(http.Request) handler,
}) => tester.pumpWidget(
  MaterialApp(
    home: RuntimeScreenPage(
      layout: ScreenLayout(name: 'My screen', widgets: widgets.cast()),
      groups: groups,
      deploymentBase: Uri.parse('http://h/gen/abc/'),
      actionClient: ScreenActionClient(httpClient: MockClient(handler), timeout: const Duration(seconds: 1)),
    ),
  ),
);

void main() {
  group('RuntimeScreenPage', () {
    testWidgets('renders a label, a field and a button as designed', (tester) async {
      await _pump(
        tester,
        widgets: const [
          LabelWidgetConfig(id: 'w1', x: 0, y: 0, text: 'Class A'),
          FieldWidgetConfig(id: 'w2', x: 0, y: 40, groupName: 'class-a-controller', fieldName: 'edad'),
          ButtonWidgetConfig(id: 'w3', x: 0, y: 80, groupName: 'class-a-controller', action: ScreenAction.list),
        ],
        handler: (_) async => http.Response('[]', 200),
      );

      expect(find.text('Class A'), findsOneWidget);
      expect(find.widgetWithText(TextField, 'edad'), findsOneWidget);
      expect(find.widgetWithText(FilledButton, 'list'), findsOneWidget);
    });

    testWidgets('the list button calls GET on its class\'s collection path and shows the result', (tester) async {
      late Uri seen;
      await _pump(
        tester,
        widgets: const [ButtonWidgetConfig(id: 'w1', x: 0, y: 0, groupName: 'class-a-controller', action: ScreenAction.list)],
        handler: (request) async {
          seen = request.url;
          return http.Response(jsonEncode([1, 2, 3]), 200);
        },
      );

      await tester.tap(find.widgetWithText(FilledButton, 'list'));
      await tester.pumpAndSettle();

      expect(seen.toString(), 'http://h/gen/abc/api/class-as');
      expect(find.textContaining('1'), findsWidgets);
    });

    testWidgets('typing into a field and tapping create sends it in the request body', (tester) async {
      late String seenBody;
      await _pump(
        tester,
        widgets: const [
          FieldWidgetConfig(id: 'w1', x: 0, y: 0, groupName: 'class-a-controller', fieldName: 'edad'),
          ButtonWidgetConfig(id: 'w2', x: 0, y: 40, groupName: 'class-a-controller', action: ScreenAction.create),
        ],
        handler: (request) async {
          seenBody = request.body;
          return http.Response('', 201);
        },
      );

      await tester.enterText(find.widgetWithText(TextField, 'edad'), '30');
      await tester.tap(find.widgetWithText(FilledButton, 'create'));
      await tester.pumpAndSettle();

      expect(jsonDecode(seenBody), {'edad': '30'});
      expect(find.text('Done.'), findsOneWidget);
    });

    testWidgets('a mixed screen only sends the tapped button\'s own class fields, and hits that class\'s endpoint', (
      tester,
    ) async {
      final seenUrls = <Uri>[];
      final seenBodies = <String>[];
      await _pump(
        tester,
        groups: const [_classA, _classB],
        widgets: const [
          FieldWidgetConfig(id: 'fa', x: 0, y: 0, groupName: 'class-a-controller', fieldName: 'edad'),
          ButtonWidgetConfig(id: 'ba', x: 0, y: 40, groupName: 'class-a-controller', action: ScreenAction.create),
          FieldWidgetConfig(id: 'fb', x: 100, y: 0, groupName: 'class-b-controller', fieldName: 'name'),
          ButtonWidgetConfig(id: 'bb', x: 100, y: 40, groupName: 'class-b-controller', action: ScreenAction.create),
        ],
        handler: (request) async {
          seenUrls.add(request.url);
          seenBodies.add(request.body);
          return http.Response('', 201);
        },
      );

      await tester.enterText(find.widgetWithText(TextField, 'edad'), '20');
      await tester.enterText(find.widgetWithText(TextField, 'name'), 'Ana');
      await tester.tap(find.widgetWithText(FilledButton, 'create').first); // Class A's create
      await tester.pumpAndSettle();

      expect(seenUrls.single.toString(), 'http://h/gen/abc/api/class-as');
      expect(jsonDecode(seenBodies.single), {'edad': '20'}); // not {'edad': '20', 'name': 'Ana'}
    });

    testWidgets('a server error shows its message', (tester) async {
      await _pump(
        tester,
        widgets: const [ButtonWidgetConfig(id: 'w1', x: 0, y: 0, groupName: 'class-a-controller', action: ScreenAction.list)],
        handler: (_) async => http.Response('nope', 500),
      );

      await tester.tap(find.widgetWithText(FilledButton, 'list'));
      await tester.pumpAndSettle();

      expect(find.textContaining('500'), findsOneWidget);
    });
  });
}

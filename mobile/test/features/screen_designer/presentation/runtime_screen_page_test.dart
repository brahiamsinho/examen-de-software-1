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

const _group = EndpointGroup(
  name: 'class-a-controller',
  endpoints: [
    ApiEndpoint(method: 'GET', path: '/api/class-as'),
    ApiEndpoint(method: 'POST', path: '/api/class-as'),
  ],
);

Future<void> _pump(
  WidgetTester tester, {
  required List<Object> widgets,
  required Future<http.Response> Function(http.Request) handler,
}) => tester.pumpWidget(
  MaterialApp(
    home: RuntimeScreenPage(
      layout: ScreenLayout(groupName: _group.name, widgets: widgets.cast()),
      group: _group,
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
          FieldWidgetConfig(id: 'w2', x: 0, y: 40, fieldName: 'edad'),
          ButtonWidgetConfig(id: 'w3', x: 0, y: 80, action: ScreenAction.list),
        ],
        handler: (_) async => http.Response('[]', 200),
      );

      expect(find.text('Class A'), findsOneWidget);
      expect(find.widgetWithText(TextField, 'edad'), findsOneWidget);
      expect(find.widgetWithText(FilledButton, 'list'), findsOneWidget);
    });

    testWidgets('the list button calls GET on the collection path and shows the result', (tester) async {
      late Uri seen;
      await _pump(
        tester,
        widgets: const [ButtonWidgetConfig(id: 'w1', x: 0, y: 0, action: ScreenAction.list)],
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
          FieldWidgetConfig(id: 'w1', x: 0, y: 0, fieldName: 'edad'),
          ButtonWidgetConfig(id: 'w2', x: 0, y: 40, action: ScreenAction.create),
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

    testWidgets('a server error shows its message', (tester) async {
      await _pump(
        tester,
        widgets: const [ButtonWidgetConfig(id: 'w1', x: 0, y: 0, action: ScreenAction.list)],
        handler: (_) async => http.Response('nope', 500),
      );

      await tester.tap(find.widgetWithText(FilledButton, 'list'));
      await tester.pumpAndSettle();

      expect(find.textContaining('500'), findsOneWidget);
    });
  });
}

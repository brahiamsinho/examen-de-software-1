import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/features/api_connection/data/openapi_client.dart';
import 'package:mobile/features/api_connection/presentation/connect_controller.dart';
import 'package:mobile/features/api_connection/presentation/connect_page.dart';

final _validBody = jsonEncode({
  'openapi': '3.1.0',
  'info': {'title': 'Demo API', 'version': '1.0'},
  'paths': {
    '/api/things': {
      'get': {
        'tags': ['thing-controller'],
      },
    },
  },
});

Future<void> _pump(
  WidgetTester tester,
  Future<http.Response> Function(http.Request) handler, {
  String initialUrl = '',
}) {
  final controller = ConnectController(
    client: OpenApiClient(
      httpClient: MockClient(handler),
      timeout: const Duration(seconds: 1),
    ),
  );
  return tester.pumpWidget(
    MaterialApp(
      home: ConnectPage(controller: controller, initialUrl: initialUrl),
    ),
  );
}

Finder get _field => find.byType(TextField);
Finder get _connectButton => find.widgetWithText(FilledButton, 'Connect');

void main() {
  testWidgets('shows the title and an empty field by default', (tester) async {
    await _pump(tester, (_) async => http.Response(_validBody, 200));

    expect(find.text('Connect to generated API'), findsOneWidget);
    expect(tester.widget<TextField>(_field).controller!.text, isEmpty);
  });

  testWidgets('pre-fills the field from initialUrl', (tester) async {
    await _pump(
      tester,
      (_) async => http.Response(_validBody, 200),
      initialUrl: 'https://demo.example.com/gen/abc',
    );

    expect(
      tester.widget<TextField>(_field).controller!.text,
      'https://demo.example.com/gen/abc',
    );
  });

  testWidgets('an empty submission shows the invalid URL message', (
    tester,
  ) async {
    await _pump(tester, (_) async => http.Response(_validBody, 200));

    await tester.tap(_connectButton);
    await tester.pump();

    expect(find.text('Enter a valid http:// or https:// URL.'), findsOneWidget);
  });

  testWidgets('shows progress and disables the button while loading', (
    tester,
  ) async {
    final gate = Completer<http.Response>();
    await _pump(tester, (_) => gate.future);

    await tester.enterText(_field, 'https://demo.example.com');
    await tester.tap(_connectButton);
    await tester.pump();

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(tester.widget<FilledButton>(find.byType(FilledButton)).onPressed, isNull);

    gate.complete(http.Response(_validBody, 200));
    await tester.pumpAndSettle();
  });

  testWidgets('a failure shows its message and keeps the typed URL', (
    tester,
  ) async {
    await _pump(
      tester,
      (_) async => throw http.ClientException('Connection refused'),
    );

    await tester.enterText(_field, 'https://demo.example.com');
    await tester.tap(_connectButton);
    await tester.pumpAndSettle();

    expect(
      find.text('Could not reach the server. Check the URL and your network.'),
      findsOneWidget,
    );
    expect(
      tester.widget<TextField>(_field).controller!.text,
      'https://demo.example.com',
    );
  });

  testWidgets('a success opens the discovery screen', (tester) async {
    await _pump(tester, (_) async => http.Response(_validBody, 200));

    await tester.enterText(_field, 'https://demo.example.com/gen/abc');
    await tester.tap(_connectButton);
    await tester.pumpAndSettle();

    expect(find.text('Demo API'), findsOneWidget);
    expect(find.text('thing-controller'), findsOneWidget);
    expect(find.text('GET'), findsOneWidget);
    expect(find.text('/api/things'), findsOneWidget);
  });
}

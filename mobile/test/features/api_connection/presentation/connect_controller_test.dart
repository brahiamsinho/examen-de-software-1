import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/features/api_connection/data/openapi_client.dart';
import 'package:mobile/features/api_connection/domain/connection_failure.dart';
import 'package:mobile/features/api_connection/presentation/connect_controller.dart';

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

class _Harness {
  _Harness(Future<http.Response> Function(http.Request) handler) {
    controller = ConnectController(
      client: OpenApiClient(
        httpClient: MockClient((request) {
          requests.add(request.url);
          return handler(request);
        }),
        timeout: const Duration(seconds: 1),
      ),
    );
    controller.addListener(() => states.add(controller.state));
  }

  late final ConnectController controller;
  final requests = <Uri>[];
  final states = <ConnectState>[];
}

void main() {
  group('ConnectController', () {
    test('starts idle', () {
      final h = _Harness((_) async => http.Response(_validBody, 200));

      expect(h.controller.state, isA<ConnectIdle>());
    });

    test('goes loading -> success and requests the normalized URL', () async {
      final h = _Harness((_) async => http.Response(_validBody, 200));

      await h.controller.connect('https://demo.example.com/gen/abc/');

      expect(h.states.map((s) => s.runtimeType), [
        ConnectLoading,
        ConnectSuccess,
      ]);
      final success = h.controller.state as ConnectSuccess;
      expect(success.discovery.title, 'Demo API');
      expect(
        success.openApiUri.toString(),
        'https://demo.example.com/gen/abc/v3/api-docs',
      );
      expect(h.requests.single, success.openApiUri);
    });

    test('an invalid URL fails without touching the network', () async {
      final h = _Harness((_) async => http.Response(_validBody, 200));

      await h.controller.connect('not a url');

      final failed = h.controller.state as ConnectFailed;
      expect(failed.failure.kind, ConnectionFailureKind.invalidUrl);
      expect(h.requests, isEmpty);
    });

    test('a server error becomes a failed state', () async {
      final h = _Harness((_) async => http.Response('boom', 500));

      await h.controller.connect('https://demo.example.com');

      final failed = h.controller.state as ConnectFailed;
      expect(failed.failure.kind, ConnectionFailureKind.httpStatus);
      expect(failed.failure.statusCode, 500);
    });

    test('ignores a second submission while loading', () async {
      final gate = Completer<http.Response>();
      final h = _Harness((_) => gate.future);

      final first = h.controller.connect('https://demo.example.com');
      await h.controller.connect('https://other.example.com');
      gate.complete(http.Response(_validBody, 200));
      await first;

      expect(h.requests, hasLength(1));
      expect(h.controller.state, isA<ConnectSuccess>());
    });

    test('ignores a response that arrives after reset', () async {
      final gate = Completer<http.Response>();
      final h = _Harness((_) => gate.future);

      final pending = h.controller.connect('https://demo.example.com');
      h.controller.reset();
      gate.complete(http.Response(_validBody, 200));
      await pending;

      expect(h.controller.state, isA<ConnectIdle>());
    });

    test('reset returns to idle after a failure', () async {
      final h = _Harness((_) async => http.Response('nope', 404));

      await h.controller.connect('https://demo.example.com');
      h.controller.reset();

      expect(h.controller.state, isA<ConnectIdle>());
    });
  });
}

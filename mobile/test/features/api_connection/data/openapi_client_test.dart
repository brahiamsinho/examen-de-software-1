import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/features/api_connection/data/openapi_client.dart';
import 'package:mobile/features/api_connection/domain/connection_failure.dart';

final _uri = Uri.parse('https://demo.example.com/gen/abc/v3/api-docs');

const _validDocument = {
  'openapi': '3.1.0',
  'info': {'title': 'Demo API', 'version': '1.0'},
  'paths': {
    '/api/things': {
      'get': {
        'tags': ['thing-controller'],
      },
    },
  },
};

Matcher _failure(ConnectionFailureKind kind) => throwsA(
  isA<ConnectionFailure>().having((f) => f.kind, 'kind', kind),
);

OpenApiClient _clientFor(
  Future<http.Response> Function(http.Request) handler, {
  Duration timeout = const Duration(seconds: 1),
}) => OpenApiClient(httpClient: MockClient(handler), timeout: timeout);

void main() {
  group('OpenApiClient.fetch', () {
    test('returns the discovery of a valid document and asks for JSON', () async {
      late http.Request seen;
      final client = _clientFor((request) async {
        seen = request;
        return http.Response(jsonEncode(_validDocument), 200);
      });

      final result = await client.fetch(_uri);

      expect(seen.url, _uri);
      expect(seen.method, 'GET');
      expect(seen.headers['Accept'], 'application/json');
      expect(result.title, 'Demo API');
      expect(result.endpointCount, 1);
    });

    test('maps a non-200 response to httpStatus with the code', () async {
      final client = _clientFor((_) async => http.Response('nope', 404));

      await expectLater(
        client.fetch(_uri),
        throwsA(
          isA<ConnectionFailure>()
              .having((f) => f.kind, 'kind', ConnectionFailureKind.httpStatus)
              .having((f) => f.statusCode, 'statusCode', 404),
        ),
      );
    });

    test('maps an HTML body to notJson', () async {
      final client = _clientFor(
        (_) async => http.Response('<html>Login</html>', 200),
      );

      await expectLater(
        client.fetch(_uri),
        _failure(ConnectionFailureKind.notJson),
      );
    });

    test('maps a JSON body that is not OpenAPI 3 to invalidOpenApi', () async {
      final client = _clientFor(
        (_) async => http.Response(jsonEncode({'swagger': '2.0'}), 200),
      );

      await expectLater(
        client.fetch(_uri),
        _failure(ConnectionFailureKind.invalidOpenApi),
      );
    });

    test('maps a slow response to timeout', () async {
      final client = _clientFor(
        (_) async {
          await Future<void>.delayed(const Duration(milliseconds: 300));
          return http.Response(jsonEncode(_validDocument), 200);
        },
        timeout: const Duration(milliseconds: 20),
      );

      await expectLater(
        client.fetch(_uri),
        _failure(ConnectionFailureKind.timeout),
      );
    });

    test('maps a transport error to network', () async {
      final client = _clientFor(
        (_) async => throw http.ClientException('Connection refused'),
      );

      await expectLater(
        client.fetch(_uri),
        _failure(ConnectionFailureKind.network),
      );
    });
  });
}

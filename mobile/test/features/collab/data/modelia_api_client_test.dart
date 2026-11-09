import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/features/collab/data/modelia_api_client.dart';
import 'package:mobile/features/collab/domain/api_failure.dart';

http.Response _json(Object body, [int status = 200]) =>
    http.Response(jsonEncode(body), status, headers: {'content-type': 'application/json'});

ModeliaApiClient _client(
  MockClient mock, {
  String? token = 'tok',
  int maxRetries = 2,
  void Function()? onUnauthorized,
  List<Duration>? sleeps,
}) {
  return ModeliaApiClient(
    baseUrl: 'https://modelia.test',
    httpClient: mock,
    tokenProvider: () => token,
    onUnauthorized: onUnauthorized,
    maxRetries: maxRetries,
    timeout: const Duration(milliseconds: 200),
    sleep: (d) async => sleeps?.add(d),
  );
}

void main() {
  group('requests', () {
    test('sends the bearer token and JSON headers, and resolves the path against the base URL', () async {
      late http.Request seen;
      final client = _client(MockClient((r) async {
        seen = r;
        return _json({'ok': true});
      }));

      final body = await client.getJson('/api/orgs', query: {'limit': '5'});

      expect(body, {'ok': true});
      expect(seen.url.toString(), 'https://modelia.test/api/orgs?limit=5');
      expect(seen.headers['Authorization'], 'Bearer tok');
      expect(seen.headers['Accept'], 'application/json');
    });

    test('sends no Authorization header when there is no token (login)', () async {
      late http.Request seen;
      final client = _client(MockClient((r) async {
        seen = r;
        return _json({'ok': true});
      }), token: null);

      await client.postJson('/api/auth/mobile-token', {'email': 'a@b.c'});

      expect(seen.headers.containsKey('Authorization'), isFalse);
      expect(seen.headers['Content-Type'], startsWith('application/json'));
      expect(jsonDecode(seen.body), {'email': 'a@b.c'});
    });

    test('a trailing slash in the base URL does not double the slash', () async {
      late http.Request seen;
      final client = ModeliaApiClient(
        baseUrl: 'https://modelia.test/',
        httpClient: MockClient((r) async {
          seen = r;
          return _json({});
        }),
        tokenProvider: () => null,
      );

      await client.getJson('/api/orgs');

      expect(seen.url.toString(), 'https://modelia.test/api/orgs');
    });

    test('a write can be given a longer timeout than the default (the AI may take a while to answer)', () async {
      final client = _client(MockClient((r) async {
        await Future<void>.delayed(const Duration(milliseconds: 500));
        return _json({'ok': true});
      }));

      await expectLater(client.postJson('/api/x', {}), throwsA(isA<ApiFailure>()));
      expect(
        await client.postJson('/api/x', {}, timeout: const Duration(seconds: 5)),
        {'ok': true},
      );
    });

    test('a 204 answers null instead of failing to parse an empty body', () async {
      final client = _client(MockClient((r) async => http.Response('', 204)));

      expect(await client.postJson('/api/auth/mobile-token/revoke', null), isNull);
    });
  });

  group('failures map to a kind the screen can explain', () {
    Future<ApiFailure> failure(MockClient mock, {void Function()? onUnauthorized}) async {
      final client = _client(mock, onUnauthorized: onUnauthorized, maxRetries: 0);
      try {
        await client.getJson('/api/x');
      } on ApiFailure catch (e) {
        return e;
      }
      fail('expected an ApiFailure');
    }

    test('a refused connection is offline', () async {
      final e = await failure(MockClient((r) async => throw http.ClientException('no route')));
      expect(e.kind, ApiFailureKind.offline);
    });

    test('a slow server is a timeout', () async {
      final e = await failure(MockClient((r) async {
        await Future<void>.delayed(const Duration(seconds: 2));
        return _json({});
      }));
      expect(e.kind, ApiFailureKind.timeout);
    });

    test('an invalid token is unauthorized and notifies the session once', () async {
      var notified = 0;
      final e = await failure(
        MockClient((r) async => _json({'detail': 'Invalid or expired token.', 'code': 'invalid_token'}, 401)),
        onUnauthorized: () => notified++,
      );
      expect(e.kind, ApiFailureKind.unauthorized);
      expect(e.message, 'Invalid or expired token.');
      expect(notified, 1);
    });

    test('403 / 404 / 409 / 422 / 5xx keep their meaning and the backend detail', () async {
      Future<ApiFailure> with_(int status) =>
          failure(MockClient((r) async => _json({'detail': 'detail $status'}, status)));

      expect((await with_(403)).kind, ApiFailureKind.forbidden);
      expect((await with_(404)).kind, ApiFailureKind.notFound);
      expect((await with_(409)).kind, ApiFailureKind.conflict);
      expect((await with_(422)).kind, ApiFailureKind.validation);
      expect((await with_(502)).kind, ApiFailureKind.server);
      expect((await with_(404)).message, 'detail 404');
    });

    test('a non-JSON error body still yields a failure, without a crash', () async {
      final e = await failure(MockClient((r) async => http.Response('<html>oops</html>', 500)));
      expect(e.kind, ApiFailureKind.server);
      expect(e.message, isNull);
    });

    test('a 200 with a body that is not JSON is unexpected', () async {
      final e = await failure(MockClient((r) async => http.Response('not json', 200)));
      expect(e.kind, ApiFailureKind.unexpected);
    });
  });

  group('retries (S4: reads retry, writes never repeat silently)', () {
    test('a GET retries a network error with growing delays and then succeeds', () async {
      var calls = 0;
      final sleeps = <Duration>[];
      final client = _client(MockClient((r) async {
        calls++;
        if (calls < 3) throw http.ClientException('flaky');
        return _json({'ok': true});
      }), sleeps: sleeps);

      expect(await client.getJson('/api/x'), {'ok': true});
      expect(calls, 3);
      expect(sleeps.length, 2);
      expect(sleeps[1], greaterThan(sleeps[0]));
    });

    test('a GET retries 502/503/504 but not other statuses', () async {
      var calls = 0;
      final client = _client(MockClient((r) async {
        calls++;
        return calls == 1 ? _json({'detail': 'bad gateway'}, 502) : _json({'ok': true});
      }));
      expect(await client.getJson('/api/x'), {'ok': true});
      expect(calls, 2);

      var calls404 = 0;
      final client404 = _client(MockClient((r) async {
        calls404++;
        return _json({'detail': 'nope'}, 404);
      }));
      await expectLater(client404.getJson('/api/x'), throwsA(isA<ApiFailure>()));
      expect(calls404, 1);
    });

    test('a GET gives up after maxRetries and reports the last failure', () async {
      var calls = 0;
      final client = _client(MockClient((r) async {
        calls++;
        throw http.ClientException('down');
      }));

      await expectLater(
        client.getJson('/api/x'),
        throwsA(isA<ApiFailure>().having((e) => e.kind, 'kind', ApiFailureKind.offline)),
      );
      expect(calls, 3);
    });

    test('a POST is never retried, even on a network error', () async {
      var calls = 0;
      final client = _client(MockClient((r) async {
        calls++;
        throw http.ClientException('flaky');
      }));

      await expectLater(client.postJson('/api/x', {}), throwsA(isA<ApiFailure>()));
      expect(calls, 1);
    });

    test('an unauthorized answer is never retried', () async {
      var calls = 0;
      final client = _client(MockClient((r) async {
        calls++;
        return _json({'code': 'invalid_token', 'detail': 'x'}, 401);
      }));

      await expectLater(client.getJson('/api/x'), throwsA(isA<ApiFailure>()));
      expect(calls, 1);
    });
  });
}

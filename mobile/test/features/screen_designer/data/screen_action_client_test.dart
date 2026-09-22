import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/features/screen_designer/data/screen_action_client.dart';

final _base = Uri.parse('https://demo.example.com/gen/abc/');

ScreenActionClient _clientFor(Future<http.Response> Function(http.Request) handler) =>
    ScreenActionClient(httpClient: MockClient(handler), timeout: const Duration(seconds: 1));

void main() {
  group('ScreenActionClient', () {
    test('list resolves the collection path under the deployment base and GETs it', () async {
      late http.BaseRequest seen;
      final client = _clientFor((request) async {
        seen = request;
        return http.Response(jsonEncode([1, 2]), 200);
      });

      final result = await client.list(_base, '/api/class-as');

      expect(seen.method, 'GET');
      expect(seen.url.toString(), 'https://demo.example.com/gen/abc/api/class-as');
      expect((result as ScreenActionSuccess).data, [1, 2]);
    });

    test('create POSTs the JSON body', () async {
      late http.Request seen;
      final client = _clientFor((request) async {
        seen = request;
        return http.Response(jsonEncode({'id': 1}), 201);
      });

      final result = await client.create(_base, '/api/class-as', {'edad': '20'});

      expect(seen.method, 'POST');
      expect(seen.headers['Content-Type'], 'application/json');
      expect(jsonDecode(seen.body), {'edad': '20'});
      expect(result, isA<ScreenActionSuccess>());
    });

    test('update PUTs to the collection path plus the id', () async {
      late http.BaseRequest seen;
      final client = _clientFor((request) async {
        seen = request;
        return http.Response('', 204);
      });

      final result = await client.update(_base, '/api/class-as', '7', {'edad': '21'});

      expect(seen.method, 'PUT');
      expect(seen.url.toString(), 'https://demo.example.com/gen/abc/api/class-as/7');
      expect((result as ScreenActionSuccess).data, isNull);
    });

    test('delete DELETEs the collection path plus the id', () async {
      late http.BaseRequest seen;
      final client = _clientFor((request) async {
        seen = request;
        return http.Response('', 204);
      });

      await client.delete(_base, '/api/class-as', '7');

      expect(seen.method, 'DELETE');
      expect(seen.url.toString(), 'https://demo.example.com/gen/abc/api/class-as/7');
    });

    test('a non-2xx status becomes a failure with the code', () async {
      final client = _clientFor((_) async => http.Response('nope', 404));

      final result = await client.list(_base, '/api/class-as');

      expect((result as ScreenActionFailure).message, contains('404'));
    });

    test('a transport error becomes a network failure', () async {
      final client = _clientFor((_) async => throw http.ClientException('refused'));

      final result = await client.list(_base, '/api/class-as');

      expect(result, isA<ScreenActionFailure>());
    });

    test('http.ClientException (never reached the server) is marked queueable', () async {
      final client = _clientFor((_) async => throw http.ClientException('refused'));

      final result = await client.list(_base, '/api/class-as') as ScreenActionFailure;

      expect(result.isUnreachable, isTrue);
    });

    test('SocketException (never reached the server) is marked queueable', () async {
      final client = _clientFor((_) async => throw const SocketException('connection refused'));

      final result = await client.list(_base, '/api/class-as') as ScreenActionFailure;

      expect(result.isUnreachable, isTrue);
    });

    test('a timeout is never marked queueable, even though it is also a transport failure', () async {
      final client = _clientFor((_) async {
        await Future<void>.delayed(const Duration(seconds: 5));
        return http.Response('', 200);
      });

      final result = await client.list(_base, '/api/class-as') as ScreenActionFailure;

      expect(result.isUnreachable, isFalse);
    });

    test('an unrecognized exception fails safe and is not marked queueable', () async {
      final client = _clientFor((_) async => throw StateError('something else went wrong'));

      final result = await client.list(_base, '/api/class-as') as ScreenActionFailure;

      expect(result.isUnreachable, isFalse);
    });

    test('existing positional-message construction still works (backward compatible)', () {
      const failure = ScreenActionFailure('nope');

      expect(failure.message, 'nope');
      expect(failure.isUnreachable, isFalse);
    });
  });
}

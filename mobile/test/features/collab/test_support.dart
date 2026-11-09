import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/features/collab/data/auth_repository.dart';
import 'package:mobile/features/collab/data/token_storage.dart';
import 'package:mobile/features/collab/domain/organization.dart';
import 'package:mobile/features/collab/presentation/session_controller.dart';

/// Shared helpers for the collaborative-feature tests (issue #19).
class MemoryStorage implements TokenStorage {
  String? value;

  @override
  Future<String?> read() async => value;

  @override
  Future<void> write(String value) async => this.value = value;

  @override
  Future<void> clear() async => value = null;
}

const loginBody = {
  'token': 'raw-token',
  'expires_at': '2099-01-01T00:00:00Z',
  'user': {'id': 'u1', 'email': 'ana@acme.test', 'full_name': 'Ana', 'is_verified': false},
};

http.Response jsonResponse(Object body, [int status = 200]) =>
    http.Response(jsonEncode(body), status, headers: {'content-type': 'application/json'});

typedef Handler = http.Response Function(http.Request request);

/// A fake server: `'GET /api/orgs'` style keys map to handlers; the login is
/// answered automatically and everything else is a 404. Every request is
/// recorded in [seen] so a test can assert what was (not) sent.
class FakeServer {
  FakeServer(this.routes);

  final Map<String, Handler> routes;
  final List<http.Request> seen = [];

  late final MockClient client = MockClient((request) async {
    seen.add(request);
    final key = '${request.method} ${request.url.path}';
    if (key == 'POST /api/auth/mobile-token') return jsonResponse(loginBody);
    final handler = routes[key];
    if (handler == null) return jsonResponse({'detail': 'Not found'}, 404);
    return handler(request);
  });

  Iterable<http.Request> requests(String method, String path) =>
      seen.where((r) => r.method == method && r.url.path == path);
}

Future<SessionController> signedInController(FakeServer server) async {
  final controller = SessionController(
    repository: AuthRepository(storage: MemoryStorage(), httpClient: server.client),
    httpClient: server.client,
  );
  await controller.restore();
  await controller.signIn(baseUrl: 'https://modelia.test', email: 'ana@acme.test', password: 'secret');
  return controller;
}

Organization organization({MemberRole role = MemberRole.editor}) =>
    Organization(id: '1', name: 'Acme', slug: 'acme', role: role);

DocumentSummary documentSummary() =>
    DocumentSummary(id: 'd1', name: 'Ventas', revision: 3, updatedAt: DateTime.utc(2026, 11, 8, 10));

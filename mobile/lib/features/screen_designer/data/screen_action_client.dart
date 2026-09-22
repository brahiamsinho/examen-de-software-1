import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

/// What running a placed button produced: either the decoded JSON body (a
/// `List` for `list`, whatever the backend returned for the others, `null`
/// on an empty body) or a human-readable reason it failed.
sealed class ScreenActionResult {
  const ScreenActionResult();
}

class ScreenActionSuccess extends ScreenActionResult {
  const ScreenActionSuccess(this.data);

  final Object? data;
}

class ScreenActionFailure extends ScreenActionResult {
  const ScreenActionFailure(this.message);

  final String message;
}

/// Runs the four CRUD actions a placed button can trigger against a
/// generated backend's real endpoints. Separate from `OpenApiClient` (which
/// only ever reads the OpenAPI document) since this one writes data.
class ScreenActionClient {
  ScreenActionClient({http.Client? httpClient, this.timeout = const Duration(seconds: 10)})
    : _httpClient = httpClient ?? http.Client();

  final http.Client _httpClient;
  final Duration timeout;

  Future<ScreenActionResult> list(Uri deploymentBase, String collectionPath) =>
      _send('GET', _resolve(deploymentBase, collectionPath));

  Future<ScreenActionResult> create(Uri deploymentBase, String collectionPath, Map<String, Object?> body) =>
      _send('POST', _resolve(deploymentBase, collectionPath), body: body);

  Future<ScreenActionResult> update(Uri deploymentBase, String collectionPath, String id, Map<String, Object?> body) =>
      _send('PUT', _resolve(deploymentBase, '$collectionPath/$id'), body: body);

  Future<ScreenActionResult> delete(Uri deploymentBase, String collectionPath, String id) =>
      _send('DELETE', _resolve(deploymentBase, '$collectionPath/$id'));

  Uri _resolve(Uri deploymentBase, String path) =>
      deploymentBase.resolve(path.startsWith('/') ? path.substring(1) : path);

  Future<ScreenActionResult> _send(String method, Uri uri, {Map<String, Object?>? body}) async {
    http.Response response;
    try {
      final request = http.Request(method, uri)..headers['Accept'] = 'application/json';
      if (body != null) {
        request.headers['Content-Type'] = 'application/json';
        request.body = jsonEncode(body);
      }
      response = await http.Response.fromStream(await _httpClient.send(request).timeout(timeout));
    } on TimeoutException {
      return const ScreenActionFailure('The server took too long to respond.');
    } catch (_) {
      return const ScreenActionFailure('Could not reach the server. Check the URL and your network.');
    }

    if (response.statusCode < 200 || response.statusCode >= 300) {
      return ScreenActionFailure('The server responded with an error (${response.statusCode}).');
    }
    if (response.body.trim().isEmpty) {
      return const ScreenActionSuccess(null);
    }
    try {
      return ScreenActionSuccess(jsonDecode(response.body));
    } on FormatException {
      return const ScreenActionFailure('The response was not a JSON document.');
    }
  }
}

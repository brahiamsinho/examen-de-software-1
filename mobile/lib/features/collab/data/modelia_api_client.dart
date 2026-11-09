import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../domain/api_failure.dart';

/// JSON client for the Modelia API (issue #19). No `dart:io` import, so it
/// keeps compiling for web, like `OpenApiClient`.
///
/// S4 ("conexión inestable, con reintentos y estado claro"):
///  * reads (GET) retry on network errors, timeouts and 502/503/504, with a
///    growing delay;
///  * writes (POST) are NEVER retried here, because repeating one after an
///    unknown outcome could apply a change twice. The screen shows the failure
///    and lets the person decide;
///  * every failure becomes an [ApiFailure] with a kind the screen can explain.
class ModeliaApiClient {
  ModeliaApiClient({
    required String baseUrl,
    required this.tokenProvider,
    http.Client? httpClient,
    this.onUnauthorized,
    this.maxRetries = 2,
    this.timeout = const Duration(seconds: 15),
    this.retryBaseDelay = const Duration(milliseconds: 400),
    Future<void> Function(Duration)? sleep,
  }) : _baseUrl = baseUrl.trim().replaceAll(RegExp(r'/+$'), ''),
       _httpClient = httpClient ?? http.Client(),
       _sleep = sleep ?? Future<void>.delayed;

  final String _baseUrl;
  final http.Client _httpClient;
  final String? Function() tokenProvider;

  /// Called when the server says the token is invalid or expired, so the app
  /// can drop the session and ask for a new login.
  final void Function()? onUnauthorized;
  final int maxRetries;
  final Duration timeout;
  final Duration retryBaseDelay;
  final Future<void> Function(Duration) _sleep;

  Future<Object?> getJson(String path, {Map<String, String>? query}) async {
    var attempt = 0;
    while (true) {
      try {
        return await _send('GET', path, query: query);
      } on ApiFailure catch (failure) {
        if (!_isTransient(failure) || attempt >= maxRetries) rethrow;
        await _sleep(retryBaseDelay * (1 << attempt));
        attempt++;
      }
    }
  }

  /// Never retried; see the class comment.
  Future<Object?> postJson(String path, Object? body) => _send('POST', path, body: body);

  bool _isTransient(ApiFailure failure) {
    if (failure.kind == ApiFailureKind.offline || failure.kind == ApiFailureKind.timeout) return true;
    return failure.kind == ApiFailureKind.server &&
        (failure.statusCode == 502 || failure.statusCode == 503 || failure.statusCode == 504);
  }

  Future<Object?> _send(String method, String path, {Map<String, String>? query, Object? body}) async {
    var uri = Uri.parse('$_baseUrl$path');
    if (query != null && query.isNotEmpty) uri = uri.replace(queryParameters: query);
    final token = tokenProvider();
    final headers = <String, String>{
      'Accept': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
      if (method == 'POST') 'Content-Type': 'application/json; charset=utf-8',
    };

    http.Response response;
    try {
      final request = method == 'POST'
          ? _httpClient.post(uri, headers: headers, body: body == null ? null : jsonEncode(body))
          : _httpClient.get(uri, headers: headers);
      response = await request.timeout(timeout);
    } on TimeoutException {
      throw const ApiFailure(ApiFailureKind.timeout);
    } catch (_) {
      // http.ClientException, DNS, TLS, a raw socket error: all "offline".
      throw const ApiFailure(ApiFailureKind.offline);
    }

    final status = response.statusCode;
    if (status >= 200 && status < 300) {
      if (status == 204 || response.body.trim().isEmpty) return null;
      try {
        return jsonDecode(utf8.decode(response.bodyBytes));
      } on FormatException {
        throw ApiFailure(ApiFailureKind.unexpected, statusCode: status);
      }
    }

    final failure = _failureFor(status, response);
    if (failure.kind == ApiFailureKind.unauthorized && failure.code == 'invalid_token') {
      onUnauthorized?.call();
    }
    throw failure;
  }

  ApiFailure _failureFor(int status, http.Response response) {
    String? detail;
    String? code;
    try {
      final decoded = jsonDecode(utf8.decode(response.bodyBytes));
      if (decoded is Map<String, dynamic>) {
        if (decoded['detail'] is String) detail = decoded['detail'] as String;
        if (decoded['code'] is String) code = decoded['code'] as String;
      }
    } on FormatException {
      // A non-JSON error body (a proxy's HTML page): keep the status only.
    }
    final kind = switch (status) {
      401 => ApiFailureKind.unauthorized,
      403 => ApiFailureKind.forbidden,
      404 => ApiFailureKind.notFound,
      409 => ApiFailureKind.conflict,
      400 || 422 => ApiFailureKind.validation,
      429 => ApiFailureKind.server,
      >= 500 => ApiFailureKind.server,
      _ => ApiFailureKind.unexpected,
    };
    return ApiFailure(kind, statusCode: status, message: detail, code: code);
  }
}

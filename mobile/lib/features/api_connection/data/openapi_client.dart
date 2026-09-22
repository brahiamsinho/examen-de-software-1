import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../domain/api_discovery.dart';
import '../domain/connection_failure.dart';
import 'openapi_parser.dart';

/// Downloads and validates a generated backend's OpenAPI document (spec:
/// OpenAPI Document Validation). No `dart:io` import (design.md D5), so this
/// keeps compiling for `web/`; any transport error surfaces as
/// [ConnectionFailureKind.network].
class OpenApiClient {
  OpenApiClient({http.Client? httpClient, this.timeout = const Duration(seconds: 10)})
    : _httpClient = httpClient ?? http.Client();

  final http.Client _httpClient;
  final Duration timeout;

  Future<ApiDiscovery> fetch(Uri uri) async {
    http.Response response;
    try {
      response = await _httpClient.get(uri, headers: const {'Accept': 'application/json'}).timeout(timeout);
    } on TimeoutException {
      throw const ConnectionFailure(ConnectionFailureKind.timeout);
    } on http.ClientException {
      throw const ConnectionFailure(ConnectionFailureKind.network);
    } catch (_) {
      // Any other transport failure (DNS, TLS, a raw socket error, ...)
      // still maps to the same user-facing "network" failure.
      throw const ConnectionFailure(ConnectionFailureKind.network);
    }

    if (response.statusCode != 200) {
      throw ConnectionFailure(ConnectionFailureKind.httpStatus, statusCode: response.statusCode);
    }

    Object? decoded;
    try {
      decoded = jsonDecode(response.body);
    } on FormatException {
      throw const ConnectionFailure(ConnectionFailureKind.notJson);
    }

    return parseOpenApi(decoded);
  }
}

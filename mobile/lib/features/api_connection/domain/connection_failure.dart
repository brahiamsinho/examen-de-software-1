/// Every way `ConnectController.connect` can fail, each mapped to one
/// distinct, human-readable message shown on the connect screen.
enum ConnectionFailureKind {
  invalidUrl,
  timeout,
  network,
  httpStatus,
  notJson,
  invalidOpenApi,
}

/// Thrown by [normalizeOpenApiUrl], `OpenApiClient.fetch` and `parseOpenApi`.
/// `statusCode` is only set for [ConnectionFailureKind.httpStatus]; `detail`
/// is an optional extra reason, mainly for [ConnectionFailureKind.invalidOpenApi].
class ConnectionFailure implements Exception {
  const ConnectionFailure(this.kind, {this.detail, this.statusCode});

  final ConnectionFailureKind kind;
  final String? detail;
  final int? statusCode;

  /// English UI copy (design.md D9), shown as-is on the connect screen.
  String get message {
    switch (kind) {
      case ConnectionFailureKind.invalidUrl:
        return 'Enter a valid http:// or https:// URL.';
      case ConnectionFailureKind.timeout:
        return 'The server took too long to respond.';
      case ConnectionFailureKind.network:
        return 'Could not reach the server. Check the URL and your network.';
      case ConnectionFailureKind.httpStatus:
        return 'The server responded with an error${statusCode != null ? ' ($statusCode)' : ''}.';
      case ConnectionFailureKind.notJson:
        return 'The response was not a JSON document.';
      case ConnectionFailureKind.invalidOpenApi:
        return 'This does not look like an OpenAPI 3 document.';
    }
  }

  @override
  String toString() => 'ConnectionFailure($kind${detail != null ? ': $detail' : ''})';
}

import 'connection_failure.dart';

const _apiDocsSuffix = '/v3/api-docs';
const _swaggerIndexSuffix = '/swagger-ui/index.html';
const _swaggerHtmlSuffix = '/swagger-ui.html';

/// Turns whatever the user typed into the OpenAPI document URL
/// `<origin>[/prefix]/v3/api-docs` (spec: URL Normalization). Trims the
/// input, requires `http`/`https` with a non-empty host, drops query and
/// fragment, and keeps any path prefix (a generated deployment lives behind
/// `/gen/<id>/`, design.md D3). Throws [ConnectionFailure.invalidUrl] for
/// anything that isn't a well-formed http(s) URL — never lets a malformed
/// input reach the network.
Uri normalizeOpenApiUrl(String input) {
  final trimmed = input.trim();
  if (trimmed.isEmpty) {
    throw const ConnectionFailure(ConnectionFailureKind.invalidUrl);
  }

  Uri parsed;
  try {
    parsed = Uri.parse(trimmed);
  } on FormatException {
    throw const ConnectionFailure(ConnectionFailureKind.invalidUrl);
  }

  final scheme = parsed.scheme.toLowerCase();
  if ((scheme != 'http' && scheme != 'https') || parsed.host.isEmpty) {
    throw const ConnectionFailure(ConnectionFailureKind.invalidUrl);
  }

  var path = parsed.path;
  if (path.endsWith('/')) {
    path = path.substring(0, path.length - 1);
  }

  final String finalPath;
  if (path.endsWith(_apiDocsSuffix)) {
    finalPath = path;
  } else if (path.endsWith(_swaggerIndexSuffix)) {
    finalPath = '${path.substring(0, path.length - _swaggerIndexSuffix.length)}$_apiDocsSuffix';
  } else if (path.endsWith(_swaggerHtmlSuffix)) {
    finalPath = '${path.substring(0, path.length - _swaggerHtmlSuffix.length)}$_apiDocsSuffix';
  } else {
    finalPath = '$path$_apiDocsSuffix';
  }

  return Uri(
    scheme: scheme,
    host: parsed.host.toLowerCase(),
    port: parsed.hasPort ? parsed.port : null,
    path: finalPath,
  );
}

import '../domain/api_discovery.dart';
import '../domain/connection_failure.dart';

const _httpMethods = {'get', 'post', 'put', 'patch', 'delete'};

/// Pure parse of a decoded JSON document into an [ApiDiscovery] (spec:
/// OpenAPI Document Validation, Endpoint Discovery). Accepts only a JSON
/// object whose `openapi` field is a string starting with `3.` (rejects
/// Swagger 2's `swagger` field and OpenAPI 4+ alike) and whose `paths`
/// field is an object; anything else throws
/// [ConnectionFailureKind.invalidOpenApi].
ApiDiscovery parseOpenApi(Object? json) {
  if (json is! Map) {
    throw const ConnectionFailure(
      ConnectionFailureKind.invalidOpenApi,
      detail: 'The document is not a JSON object.',
    );
  }

  final openApiVersion = json['openapi'];
  if (openApiVersion is! String || !openApiVersion.startsWith('3.')) {
    throw const ConnectionFailure(
      ConnectionFailureKind.invalidOpenApi,
      detail: 'Only OpenAPI 3.x documents are supported.',
    );
  }

  final pathsRaw = json['paths'];
  if (pathsRaw is! Map) {
    throw const ConnectionFailure(
      ConnectionFailureKind.invalidOpenApi,
      detail: 'The document has no "paths" object.',
    );
  }

  final info = json['info'];
  final title = (info is Map && info['title'] is String) ? info['title'] as String : 'Untitled API';
  final version = (info is Map && info['version'] is String) ? info['version'] as String : '';

  // Insertion order == document order (jsonDecode preserves it), and it is
  // preserved into each group's endpoint list, matching the spec's "keeps
  // document order" requirement.
  final endpointsByGroup = <String, List<ApiEndpoint>>{};
  for (final pathEntry in pathsRaw.entries) {
    final path = pathEntry.key.toString();
    final pathItem = pathEntry.value;
    if (pathItem is! Map) continue;

    for (final operationEntry in pathItem.entries) {
      final method = operationEntry.key.toString().toLowerCase();
      // Non-method keys (e.g. a path-level `parameters` array) are not
      // endpoints and must be ignored, not misread as one.
      if (!_httpMethods.contains(method)) continue;

      final operation = operationEntry.value;
      final tags = operation is Map ? operation['tags'] : null;
      final groupName = (tags is List && tags.isNotEmpty) ? tags.first.toString() : _fallbackGroupName(path);
      final summary = (operation is Map && operation['summary'] is String) ? operation['summary'] as String : null;

      endpointsByGroup
          .putIfAbsent(groupName, () => <ApiEndpoint>[])
          .add(ApiEndpoint(method: method.toUpperCase(), path: path, summary: summary));
    }
  }

  final groupNames = endpointsByGroup.keys.toList()..sort();
  return ApiDiscovery(
    title: title,
    version: version,
    openApiVersion: openApiVersion,
    groups: [for (final name in groupNames) EndpointGroup(name: name, endpoints: endpointsByGroup[name]!)],
  );
}

/// An untagged endpoint groups by the segment after `/api/`, else its own
/// first segment, else `untagged` (design.md D4) — never dropped.
String _fallbackGroupName(String path) {
  final segments = path.split('/').where((segment) => segment.isNotEmpty).toList();
  if (segments.isEmpty) return 'untagged';
  if (segments.first == 'api') {
    return segments.length > 1 ? segments[1] : 'untagged';
  }
  return segments.first;
}

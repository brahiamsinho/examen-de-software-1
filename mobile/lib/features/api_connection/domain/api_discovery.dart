/// One HTTP method + path parsed out of an OpenAPI `paths` object.
class ApiEndpoint {
  const ApiEndpoint({required this.method, required this.path, this.summary});

  /// Upper case, e.g. `GET`.
  final String method;
  final String path;
  final String? summary;
}

/// Endpoints sharing a tag (or the fallback grouping, design.md D4).
class EndpointGroup {
  const EndpointGroup({required this.name, required this.endpoints, this.attributeNames = const []});

  final String name;
  final List<ApiEndpoint> endpoints;

  /// The class's own attribute names, resolved from its `POST` operation's
  /// request body schema (`components.schemas`) when the document declares
  /// one; empty for a group with no create endpoint (e.g. a read-only or
  /// join table) or when schema resolution fails. Lets the screen designer
  /// offer a picker instead of the user typing a name by hand.
  final List<String> attributeNames;
}

/// What `parseOpenApi` extracts from a generated backend's OpenAPI document:
/// enough to show a user what the API exposes, grouped and sorted.
class ApiDiscovery {
  const ApiDiscovery({
    required this.title,
    required this.version,
    required this.openApiVersion,
    required this.groups,
  });

  final String title;
  final String version;
  final String openApiVersion;
  final List<EndpointGroup> groups;

  int get endpointCount => groups.fold(0, (sum, group) => sum + group.endpoints.length);
}

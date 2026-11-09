import '../domain/api_failure.dart';
import '../domain/organization.dart';
import 'modelia_api_client.dart';

/// Reads and writes the collaborative data through the authenticated client
/// (issue #19). Every answer is validated here, so a screen only ever sees
/// well-formed models or an [ApiFailure].
class CollabRepository {
  const CollabRepository(this._api);

  final ModeliaApiClient _api;

  Future<List<Organization>> listOrganizations() async =>
      _list(await _api.getJson('/api/orgs'), Organization.fromJson);

  Future<List<DocumentSummary>> listDocuments(String orgSlug) async =>
      _list(await _api.getJson('${_orgPath(orgSlug)}/documents'), DocumentSummary.fromJson);

  static String _orgPath(String orgSlug) => '/api/orgs/${Uri.encodeComponent(orgSlug)}';

  /// Parses a JSON array item by item; anything malformed is `unexpected`
  /// (a contract change), never a crash on the screen.
  static List<T> _list<T>(Object? body, T Function(Object?) parse) {
    if (body is! List) throw const ApiFailure(ApiFailureKind.unexpected);
    try {
      return [for (final item in body) parse(item)];
    } on FormatException {
      throw const ApiFailure(ApiFailureKind.unexpected);
    }
  }
}

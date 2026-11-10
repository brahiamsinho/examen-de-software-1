import '../domain/activity_log.dart';
import '../domain/api_failure.dart';
import '../domain/chat.dart';
import '../domain/diagram_preview.dart';
import '../domain/organization.dart';
import '../domain/proposal.dart';
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

  Future<List<ChatMessage>> listChat(String orgSlug, String docId) async =>
      _list(await _api.getJson('${_docPath(orgSlug, docId)}/chat'), ChatMessage.fromJson);

  /// Posts a chat message. The server answers only after the AI has had its
  /// turn (when mentioned), so this waits [chatTimeout], longer than a normal
  /// call. Never retried: a timeout does not tell whether the message arrived.
  Future<ChatSendResult> sendChat(String orgSlug, String docId, String content) async {
    final body = await _api.postJson(
      '${_docPath(orgSlug, docId)}/chat',
      {'content': content},
      timeout: chatTimeout,
    );
    try {
      return ChatSendResult.fromJson(body);
    } on FormatException {
      throw const ApiFailure(ApiFailureKind.unexpected);
    }
  }

  /// The latest entries of the diagram's log, newest first.
  /// The diagram itself, only to look at it (never to edit it from the phone).
  Future<DiagramPreview> getDiagram(String orgSlug, String docId) async {
    final body = await _api.getJson(_docPath(orgSlug, docId));
    if (body is! Map) throw const ApiFailure(ApiFailureKind.unexpected);
    try {
      return DiagramPreview.fromJson(body.cast<String, Object?>());
    } on TypeError {
      throw const ApiFailure(ApiFailureKind.unexpected);
    }
  }

  Future<List<LogEntry>> listLog(String orgSlug, String docId, {int limit = 100}) async {
    final entries = _list(
      await _api.getJson('${_docPath(orgSlug, docId)}/log', query: {'limit': '$limit'}),
      LogEntry.fromJson,
    );
    entries.sort((a, b) => b.id.compareTo(a.id));
    return entries;
  }

  Future<List<Proposal>> listProposals(String orgSlug, String docId) async =>
      _list(await _api.getJson('${_docPath(orgSlug, docId)}/ai-proposals'), Proposal.fromJson);

  /// Applies every change of the draft to the shared diagram. Never retried:
  /// repeating it after an unknown outcome could not be told from a second,
  /// different decision.
  Future<Proposal> approveProposal(String orgSlug, String docId, String proposalId) =>
      _decide(orgSlug, docId, proposalId, 'approve');

  Future<Proposal> rejectProposal(String orgSlug, String docId, String proposalId) =>
      _decide(orgSlug, docId, proposalId, 'reject');

  Future<Proposal> _decide(String orgSlug, String docId, String proposalId, String verb) async {
    final body = await _api.postJson(
      '${_docPath(orgSlug, docId)}/ai-proposals/${Uri.encodeComponent(proposalId)}/$verb',
      null,
    );
    try {
      return Proposal.fromJson(body);
    } on FormatException {
      throw const ApiFailure(ApiFailureKind.unexpected);
    }
  }

  /// Longer than the server's own AI timeout (120 s by default), so the phone
  /// does not give up before the server does.
  static const chatTimeout = Duration(seconds: 150);

  static String _orgPath(String orgSlug) => '/api/orgs/${Uri.encodeComponent(orgSlug)}';

  static String _docPath(String orgSlug, String docId) =>
      '${_orgPath(orgSlug)}/documents/${Uri.encodeComponent(docId)}';

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

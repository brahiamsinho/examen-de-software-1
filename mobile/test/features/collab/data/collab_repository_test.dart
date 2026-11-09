import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/features/collab/data/collab_repository.dart';
import 'package:mobile/features/collab/data/modelia_api_client.dart';
import 'package:mobile/features/collab/domain/api_failure.dart';
import 'package:mobile/features/collab/domain/organization.dart';

http.Response _json(Object body, [int status = 200]) =>
    http.Response(jsonEncode(body), status, headers: {'content-type': 'application/json'});

CollabRepository _repo(MockClient mock) => CollabRepository(
  ModeliaApiClient(baseUrl: 'https://modelia.test', tokenProvider: () => 't', httpClient: mock, maxRetries: 0),
);

void main() {
  group('organizations', () {
    test('lists the user organizations with their role', () async {
      late http.Request seen;
      final repo = _repo(MockClient((r) async {
        seen = r;
        return _json([
          {'id': '1', 'name': 'Acme', 'slug': 'acme', 'plan': 'STARTER', 'my_role': 'OWNER'},
          {'id': '2', 'name': 'Beta', 'slug': 'beta', 'plan': 'STARTER', 'my_role': 'VIEWER'},
        ]);
      }));

      final orgs = await repo.listOrganizations();

      expect(seen.url.path, '/api/orgs');
      expect(orgs.map((o) => o.slug), ['acme', 'beta']);
      expect(orgs[0].role, MemberRole.owner);
      expect(orgs[1].role, MemberRole.viewer);
    });

    test('an unknown role is treated as read-only, never as a writer', () async {
      final repo = _repo(MockClient((r) async => _json([
        {'id': '1', 'name': 'Acme', 'slug': 'acme', 'my_role': 'SUPERADMIN'},
      ])));

      expect((await repo.listOrganizations()).single.role, MemberRole.viewer);
    });

    test('an answer that is not a list is unexpected', () async {
      final repo = _repo(MockClient((r) async => _json({'oops': true})));

      await expectLater(
        repo.listOrganizations(),
        throwsA(isA<ApiFailure>().having((e) => e.kind, 'kind', ApiFailureKind.unexpected)),
      );
    });

    test('an item without a slug is unexpected, not a crash', () async {
      final repo = _repo(MockClient((r) async => _json([{'id': '1', 'name': 'x'}])));

      await expectLater(
        repo.listOrganizations(),
        throwsA(isA<ApiFailure>().having((e) => e.kind, 'kind', ApiFailureKind.unexpected)),
      );
    });
  });

  group('roles', () {
    test('only owners and editors can write', () {
      expect(MemberRole.owner.canWrite, isTrue);
      expect(MemberRole.editor.canWrite, isTrue);
      expect(MemberRole.viewer.canWrite, isFalse);
    });

    test('labels are neutral Spanish', () {
      expect(MemberRole.owner.label, 'Propietario');
      expect(MemberRole.editor.label, 'Editor');
      expect(MemberRole.viewer.label, 'Lector');
    });
  });

  group('proposals', () {
    Map<String, Object?> proposal(String status) => {
      'id': 'p1',
      'status': status,
      'prompt': 'Agrega Rol',
      'requested_by': 'Ana',
      'created_at': '2026-11-08T17:05:00Z',
      'changes': [
        {'ok': true, 'message': 'Created class Rol'},
        {'ok': false, 'message': 'Nope'},
      ],
    };

    test('lists drafts with their changes and whether all can be applied', () async {
      late http.Request seen;
      final repo = _repo(MockClient((r) async {
        seen = r;
        return _json([proposal('pending')]);
      }));

      final drafts = await repo.listProposals('acme', 'd1');

      expect(seen.url.path, '/api/orgs/acme/documents/d1/ai-proposals');
      expect(drafts.single.requestedBy, 'Ana');
      expect(drafts.single.changes.length, 2);
      expect(drafts.single.isPending, isTrue);
      expect(drafts.single.canApprove, isFalse); // one change is not ok
    });

    test('approve and reject post to their own paths and return the decided draft', () async {
      final seen = <String>[];
      final repo = _repo(MockClient((r) async {
        seen.add('${r.method} ${r.url.path}');
        return _json(proposal(r.url.path.endsWith('approve') ? 'approved' : 'rejected'));
      }));

      final approved = await repo.approveProposal('acme', 'd1', 'p1');
      final rejected = await repo.rejectProposal('acme', 'd1', 'p1');

      expect(seen, [
        'POST /api/orgs/acme/documents/d1/ai-proposals/p1/approve',
        'POST /api/orgs/acme/documents/d1/ai-proposals/p1/reject',
      ]);
      expect(approved.status, 'approved');
      expect(rejected.status, 'rejected');
    });

    test('a draft with no changes cannot be approved', () async {
      final repo = _repo(MockClient((r) async => _json([{...proposal('pending'), 'changes': []}])));

      expect((await repo.listProposals('acme', 'd1')).single.canApprove, isFalse);
    });

    test('a malformed draft is unexpected, not a crash', () async {
      final repo = _repo(MockClient((r) async => _json([{'id': 'p1'}])));

      await expectLater(
        repo.listProposals('acme', 'd1'),
        throwsA(isA<ApiFailure>().having((e) => e.kind, 'kind', ApiFailureKind.unexpected)),
      );
    });
  });

  group('documents', () {
    test('lists the diagrams of one organization, encoding the slug in the path', () async {
      late http.Request seen;
      final repo = _repo(MockClient((r) async {
        seen = r;
        return _json([
          {'id': 'd1', 'name': 'Ventas', 'revision': 3, 'updated_at': '2026-11-08T10:00:00Z'},
          {'id': 'd2', 'name': '', 'revision': 1, 'updated_at': '2026-11-07T10:00:00Z'},
        ]);
      }));

      final docs = await repo.listDocuments('mi org/x');

      expect(seen.url.toString(), 'https://modelia.test/api/orgs/mi%20org%2Fx/documents');
      expect(docs.map((d) => d.id), ['d1', 'd2']);
      expect(docs[0].revision, 3);
      expect(docs[0].updatedAt, DateTime.utc(2026, 11, 8, 10));
      expect(docs[0].displayName, 'Ventas');
      expect(docs[1].displayName, 'Sin título');
    });

    test('another organization answers 404 and it surfaces as notFound', () async {
      final repo = _repo(MockClient((r) async => _json({'detail': 'Not found'}, 404)));

      await expectLater(
        repo.listDocuments('other'),
        throwsA(isA<ApiFailure>().having((e) => e.kind, 'kind', ApiFailureKind.notFound)),
      );
    });
  });
}

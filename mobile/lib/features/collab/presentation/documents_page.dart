import 'package:flutter/material.dart';

import '../domain/organization.dart';
import 'diagram_page.dart';
import 'format.dart';
import 'session_controller.dart';
import 'widgets/remote_data.dart';

/// The diagrams of one organization (issue #19, S2). The server returns only
/// what the person's membership allows; another organization is a 404.
class DocumentsPage extends StatelessWidget {
  const DocumentsPage({super.key, required this.controller, required this.organization});

  final SessionController controller;
  final Organization organization;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(organization.name)),
      body: RemoteData<List<DocumentSummary>>(
        load: () => controller.run((repository) => repository.listDocuments(organization.slug)),
        isEmpty: (documents) => documents.isEmpty,
        emptyMessage: 'Esta organización todavía no tiene diagramas.',
        builder: (context, documents) => ListView.separated(
          itemCount: documents.length,
          separatorBuilder: (_, _) => const Divider(height: 1),
          itemBuilder: (context, index) {
            final document = documents[index];
            return ListTile(
              leading: const Icon(Icons.account_tree_outlined),
              title: Text(document.displayName),
              subtitle: Text('rev. ${document.revision} · ${formatDateTime(document.updatedAt)}'),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => DiagramPage(controller: controller, organization: organization, document: document),
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

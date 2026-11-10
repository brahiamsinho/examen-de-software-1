import 'package:flutter/material.dart';

import '../domain/organization.dart';
import 'changes_tab.dart';
import 'chat_tab.dart';
import 'diagram_preview_tab.dart';
import 'proposals_tab.dart';
import 'session_controller.dart';

/// One diagram, seen from the phone (issue #19): its chat with the AI, the
/// drafts the AI left to approve or reject, what changed, and a read-only
/// preview of the diagram. Editing the canvas is out of scope.
class DiagramPage extends StatelessWidget {
  const DiagramPage({super.key, required this.controller, required this.organization, required this.document});

  final SessionController controller;
  final Organization organization;
  final DocumentSummary document;

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 4,
      child: Scaffold(
        appBar: AppBar(
          title: Text(document.displayName),
          bottom: const TabBar(
            tabs: [Tab(text: 'Chat'), Tab(text: 'Propuestas'), Tab(text: 'Cambios'), Tab(text: 'Diagrama')],
          ),
        ),
        body: TabBarView(
          children: [
            ChatTab(controller: controller, organization: organization, document: document),
            ProposalsTab(controller: controller, organization: organization, document: document),
            ChangesTab(controller: controller, organization: organization, document: document),
            DiagramPreviewTab(controller: controller, organization: organization, document: document),
          ],
        ),
      ),
    );
  }
}

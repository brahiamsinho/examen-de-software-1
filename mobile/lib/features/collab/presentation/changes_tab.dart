import 'package:flutter/material.dart';

import '../domain/activity_log.dart';
import '../domain/organization.dart';
import 'format.dart';
import 'session_controller.dart';
import 'widgets/remote_data.dart';

/// What happened in the diagram, from the session log (issue #19, S3). Read
/// only for everyone, VIEWER included; pull down to refresh.
class ChangesTab extends StatelessWidget {
  const ChangesTab({super.key, required this.controller, required this.organization, required this.document});

  final SessionController controller;
  final Organization organization;
  final DocumentSummary document;

  @override
  Widget build(BuildContext context) {
    return RemoteData<List<LogEntry>>(
      load: () => controller.run((repository) => repository.listLog(organization.slug, document.id)),
      isEmpty: (entries) => entries.isEmpty,
      emptyMessage: 'Todavía no hay cambios registrados en este diagrama.',
      builder: (context, entries) => ListView.separated(
        itemCount: entries.length,
        separatorBuilder: (_, _) => const Divider(height: 1),
        itemBuilder: (context, index) => _EntryTile(entry: entries[index]),
      ),
    );
  }
}

class _EntryTile extends StatelessWidget {
  const _EntryTile({required this.entry});

  final LogEntry entry;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final smaller = Theme.of(context).textTheme.bodySmall;
    return ListTile(
      leading: Icon(entry.isAi ? Icons.smart_toy_outlined : Icons.person_outline),
      title: Text(entry.summary),
      subtitle: Padding(
        padding: const EdgeInsets.only(top: 4),
        child: Wrap(
          spacing: 8,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            DecoratedBox(
              decoration: BoxDecoration(
                color: scheme.secondaryContainer,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                child: Text(entry.kindLabel, style: smaller),
              ),
            ),
            Text('${entry.author} · ${formatDateTime(entry.createdAt)}', style: smaller),
          ],
        ),
      ),
    );
  }
}

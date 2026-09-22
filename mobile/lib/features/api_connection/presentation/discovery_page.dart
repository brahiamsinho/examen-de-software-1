import 'package:flutter/material.dart';

import '../../screen_designer/data/screen_layout_store.dart';
import '../../screen_designer/presentation/autofocus_text_field.dart';
import '../../screen_designer/presentation/designer_page.dart';
import '../domain/api_discovery.dart';
import '../domain/openapi_url.dart';

/// Shows what a connected generated backend exposes: its title/version and
/// every endpoint, grouped (spec: Endpoint Discovery). Groups render
/// expanded — nothing here is worth hiding behind an extra tap for a first
/// connection. Tapping a group's name starts a new screen design that can
/// mix ALL of this backend's classes, not just the tapped one (screen_designer
/// feature, the entry point the user asked for: "armar el frontend con el
/// backend generado como Delphi o RAD Studio, con todas las clases a la vez").
/// The app bar's list icon reopens a previously saved screen by name.
class DiscoveryPage extends StatelessWidget {
  const DiscoveryPage({super.key, required this.discovery, required this.openApiUri, this.store = const ScreenLayoutStore()});

  final ApiDiscovery discovery;
  final Uri openApiUri;
  final ScreenLayoutStore store;

  Future<void> _newScreen(BuildContext context, Uri deploymentBase, {required String suggestedName}) async {
    final name = await _promptScreenName(context, title: 'New screen', initial: suggestedName);
    if (name == null || name.trim().isEmpty || !context.mounted) return;
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => ScreenDesignerPage(name: name.trim(), groups: discovery.groups, deploymentBase: deploymentBase),
      ),
    );
  }

  Future<void> _openSavedScreen(BuildContext context, Uri deploymentBase) async {
    final names = await store.listNames();
    if (!context.mounted) return;
    if (names.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('No saved screens yet')));
      return;
    }
    final chosen = await showDialog<String>(
      context: context,
      builder: (dialogContext) => SimpleDialog(
        title: const Text('Open a screen'),
        children: [
          for (final name in names)
            SimpleDialogOption(onPressed: () => Navigator.of(dialogContext).pop(name), child: Text(name)),
        ],
      ),
    );
    if (chosen == null || !context.mounted) return;
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => ScreenDesignerPage(name: chosen, groups: discovery.groups, deploymentBase: deploymentBase),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final deploymentBase = deploymentBaseFrom(openApiUri);

    return Scaffold(
      appBar: AppBar(
        title: Text(discovery.title),
        actions: [
          IconButton(
            icon: const Icon(Icons.folder_open),
            tooltip: 'Open a saved screen',
            onPressed: () => _openSavedScreen(context, deploymentBase),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'OpenAPI ${discovery.openApiVersion} · v${discovery.version} · '
            '${discovery.endpointCount} endpoint(s)',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 16),
          for (final group in discovery.groups) ...[
            InkWell(
              onTap: () => _newScreen(context, deploymentBase, suggestedName: group.name),
              child: Row(
                children: [
                  Expanded(child: Text(group.name, style: Theme.of(context).textTheme.titleMedium)),
                  const Icon(Icons.design_services, size: 18),
                ],
              ),
            ),
            for (final endpoint in group.endpoints)
              ListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                leading: SizedBox(width: 56, child: Text(endpoint.method)),
                title: Text(endpoint.path),
                subtitle: endpoint.summary != null ? Text(endpoint.summary!) : null,
              ),
            const SizedBox(height: 12),
          ],
        ],
      ),
    );
  }
}

Future<String?> _promptScreenName(BuildContext context, {required String title, required String initial}) {
  final controller = TextEditingController(text: initial);
  return showDialog<String>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: Text(title),
      content: AutofocusTextField(controller: controller, label: 'Screen name'),
      actions: [
        TextButton(onPressed: () => Navigator.of(dialogContext).pop(), child: const Text('Cancel')),
        FilledButton(onPressed: () => Navigator.of(dialogContext).pop(controller.text), child: const Text('Create')),
      ],
    ),
  );
}

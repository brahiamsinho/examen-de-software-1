import 'package:flutter/material.dart';

import '../../screen_designer/presentation/designer_page.dart';
import '../domain/api_discovery.dart';
import '../domain/openapi_url.dart';

/// Shows what a connected generated backend exposes: its title/version and
/// every endpoint, grouped (spec: Endpoint Discovery). Groups render
/// expanded — nothing here is worth hiding behind an extra tap for a first
/// connection. Tapping a group's name opens the screen designer for it
/// (screen_designer feature), the entry point the user asked for: "armar el
/// frontend con el backend generado como Delphi o RAD Studio".
class DiscoveryPage extends StatelessWidget {
  const DiscoveryPage({super.key, required this.discovery, required this.openApiUri});

  final ApiDiscovery discovery;
  final Uri openApiUri;

  @override
  Widget build(BuildContext context) {
    final deploymentBase = deploymentBaseFrom(openApiUri);

    return Scaffold(
      appBar: AppBar(title: Text(discovery.title)),
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
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => ScreenDesignerPage(group: group, deploymentBase: deploymentBase),
                ),
              ),
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

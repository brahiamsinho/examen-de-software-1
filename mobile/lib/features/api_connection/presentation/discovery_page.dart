import 'package:flutter/material.dart';

import '../domain/api_discovery.dart';

/// Shows what a connected generated backend exposes: its title/version and
/// every endpoint, grouped (spec: Endpoint Discovery). Groups render
/// expanded — nothing here is worth hiding behind an extra tap for a first
/// connection.
class DiscoveryPage extends StatelessWidget {
  const DiscoveryPage({super.key, required this.discovery});

  final ApiDiscovery discovery;

  @override
  Widget build(BuildContext context) {
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
            Text(group.name, style: Theme.of(context).textTheme.titleMedium),
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

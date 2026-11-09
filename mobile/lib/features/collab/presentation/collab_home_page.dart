import 'package:flutter/material.dart';

import '../domain/organization.dart';
import 'documents_page.dart';
import 'session_controller.dart';
import 'widgets/remote_data.dart';

/// Landing screen once signed in (issue #19): the person's organizations.
class CollabHomePage extends StatelessWidget {
  const CollabHomePage({super.key, required this.controller});

  final SessionController controller;

  @override
  Widget build(BuildContext context) {
    final session = controller.session;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Modelia'),
        actions: [
          IconButton(
            tooltip: 'Cerrar sesión',
            icon: const Icon(Icons.logout),
            onPressed: controller.signOut,
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Text(
                'Hola, ${session?.user.displayName ?? ''}',
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ),
          ),
          Expanded(
            child: RemoteData<List<Organization>>(
              load: () => controller.run((repository) => repository.listOrganizations()),
              isEmpty: (organizations) => organizations.isEmpty,
              emptyMessage: 'No perteneces a ninguna organización todavía.',
              builder: (context, organizations) => ListView.separated(
                itemCount: organizations.length,
                separatorBuilder: (_, _) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final organization = organizations[index];
                  return ListTile(
                    leading: const Icon(Icons.apartment_outlined),
                    title: Text(organization.name),
                    trailing: Text(organization.role.label),
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => DocumentsPage(controller: controller, organization: organization),
                      ),
                    ),
                  );
                },
              ),
            ),
          ),
        ],
      ),
    );
  }
}

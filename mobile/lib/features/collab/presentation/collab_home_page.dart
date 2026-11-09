import 'package:flutter/material.dart';

import 'session_controller.dart';

/// Landing screen once signed in (issue #19). Organizations and diagrams are
/// added on top of this in the next tasks.
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
      body: Center(child: Text('Hola, ${session?.user.displayName ?? ''}')),
    );
  }
}

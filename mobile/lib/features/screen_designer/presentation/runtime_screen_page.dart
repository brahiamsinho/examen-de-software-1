import 'package:flutter/material.dart';

import '../../api_connection/domain/api_discovery.dart';
import '../data/screen_action_client.dart';
import '../domain/screen_layout.dart';
import '../domain/screen_widget_config.dart';
import 'autofocus_text_field.dart';

/// Runs a saved [ScreenLayout] for real: renders each placed widget at its
/// designed position and wires buttons to the group's actual collection
/// endpoint (spec MVP — update/delete additionally ask for a record id,
/// since there is no data grid yet to pick one from). Field widgets are
/// plain `TextField`s the user types into; their current text feeds
/// create/update request bodies.
class RuntimeScreenPage extends StatefulWidget {
  const RuntimeScreenPage({
    super.key,
    required this.layout,
    required this.group,
    required this.deploymentBase,
    this.actionClient,
  });

  final ScreenLayout layout;
  final EndpointGroup group;
  final Uri deploymentBase;
  final ScreenActionClient? actionClient;

  @override
  State<RuntimeScreenPage> createState() => _RuntimeScreenPageState();
}

class _RuntimeScreenPageState extends State<RuntimeScreenPage> {
  late final ScreenActionClient _client = widget.actionClient ?? ScreenActionClient();
  final Map<String, TextEditingController> _controllers = {};
  String? _resultText;
  bool _busy = false;

  TextEditingController _controllerFor(String fieldName) =>
      _controllers.putIfAbsent(fieldName, () => TextEditingController());

  @override
  void dispose() {
    for (final controller in _controllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  /// The path a `POST` lands on, per this project's Spring generator
  /// convention: the collection path, with `/{id}` appended for a specific
  /// record (design.md `screen_designer` MVP note).
  String? get _collectionPath {
    for (final endpoint in widget.group.endpoints) {
      if (endpoint.method == 'POST') return endpoint.path;
    }
    for (final endpoint in widget.group.endpoints) {
      if (endpoint.method == 'GET' && !endpoint.path.contains('{')) return endpoint.path;
    }
    return null;
  }

  Map<String, Object?> _fieldValues() => {
    for (final placed in widget.layout.widgets)
      if (placed is FieldWidgetConfig) placed.fieldName: _controllerFor(placed.fieldName).text,
  };

  Future<String?> _promptId(String verb) => showDialog<String>(
    context: context,
    builder: (dialogContext) {
      final controller = TextEditingController();
      return AlertDialog(
        title: Text('$verb — record id'),
        content: AutofocusTextField(controller: controller, label: 'id'),
        actions: [
          TextButton(onPressed: () => Navigator.of(dialogContext).pop(), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.of(dialogContext).pop(controller.text), child: Text(verb)),
        ],
      );
    },
  );

  Future<void> _run(ScreenAction action) async {
    final path = _collectionPath;
    if (path == null) {
      setState(() => _resultText = 'This group has no collection endpoint to call.');
      return;
    }

    setState(() => _busy = true);
    ScreenActionResult result;
    switch (action) {
      case ScreenAction.list:
        result = await _client.list(widget.deploymentBase, path);
      case ScreenAction.create:
        result = await _client.create(widget.deploymentBase, path, _fieldValues());
      case ScreenAction.update:
        final id = await _promptId('Update');
        if (id == null || id.trim().isEmpty) {
          setState(() => _busy = false);
          return;
        }
        result = await _client.update(widget.deploymentBase, path, id.trim(), _fieldValues());
      case ScreenAction.delete:
        final id = await _promptId('Delete');
        if (id == null || id.trim().isEmpty) {
          setState(() => _busy = false);
          return;
        }
        result = await _client.delete(widget.deploymentBase, path, id.trim());
    }

    if (!mounted) return;
    setState(() {
      _busy = false;
      _resultText = switch (result) {
        ScreenActionSuccess(:final data) => data == null ? 'Done.' : data.toString(),
        ScreenActionFailure(:final message) => message,
      };
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.group.name)),
      body: Stack(
        children: [
          for (final config in widget.layout.widgets)
            Positioned(left: config.x, top: config.y, child: _runtimeWidgetFor(config)),
          if (_resultText != null)
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: Container(
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
                padding: const EdgeInsets.all(12),
                constraints: const BoxConstraints(maxHeight: 200),
                child: SingleChildScrollView(child: Text(_resultText!)),
              ),
            ),
          if (_busy) const Positioned(top: 8, right: 8, child: CircularProgressIndicator()),
        ],
      ),
    );
  }

  Widget _runtimeWidgetFor(ScreenWidgetConfig config) {
    return switch (config) {
      LabelWidgetConfig(:final text) => Text(text, style: Theme.of(context).textTheme.titleMedium),
      FieldWidgetConfig(:final fieldName) => SizedBox(
        width: 160,
        child: TextField(
          controller: _controllerFor(fieldName),
          decoration: InputDecoration(labelText: fieldName),
        ),
      ),
      ButtonWidgetConfig(:final action) => FilledButton(
        onPressed: _busy ? null : () => _run(action),
        child: Text(action.name),
      ),
    };
  }
}

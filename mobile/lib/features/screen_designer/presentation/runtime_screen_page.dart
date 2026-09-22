import 'package:flutter/material.dart';

import '../../api_connection/domain/api_discovery.dart';
import '../data/screen_action_client.dart';
import '../domain/screen_layout.dart';
import '../domain/screen_widget_config.dart';
import 'autofocus_text_field.dart';

/// Runs a saved [ScreenLayout] for real: renders each placed widget at its
/// designed position and wires each Button to its OWN class's (`groupName`)
/// actual collection endpoint — a screen may mix widgets from several
/// classes, so every Button/Field resolves independently rather than
/// assuming one shared class (spec MVP — update/delete additionally ask for
/// a record id, since there is no data grid yet to pick one from). Field
/// widgets are plain `TextField`s the user types into; their current text
/// feeds only the create/update calls of buttons bound to the SAME class.
class RuntimeScreenPage extends StatefulWidget {
  const RuntimeScreenPage({
    super.key,
    required this.layout,
    required this.groups,
    required this.deploymentBase,
    this.actionClient,
  });

  final ScreenLayout layout;
  final List<EndpointGroup> groups;
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

  /// The path a `POST` for `groupName` lands on, per this project's Spring
  /// generator convention: the collection path, with `/{id}` appended for a
  /// specific record (design.md `screen_designer` MVP note).
  String? _collectionPathFor(String groupName) {
    final endpoints = widget.groups.where((g) => g.name == groupName).firstOrNull?.endpoints ?? const [];
    for (final endpoint in endpoints) {
      if (endpoint.method == 'POST') return endpoint.path;
    }
    for (final endpoint in endpoints) {
      if (endpoint.method == 'GET' && !endpoint.path.contains('{')) return endpoint.path;
    }
    return null;
  }

  /// Only the Field widgets bound to the SAME class as the button that is
  /// running — a screen mixing several classes must never leak one class's
  /// typed values into another's request body.
  Map<String, Object?> _fieldValuesFor(String groupName) => {
    for (final placed in widget.layout.widgets)
      if (placed is FieldWidgetConfig && placed.groupName == groupName)
        placed.fieldName: _controllerFor('${placed.groupName}.${placed.fieldName}').text,
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

  Future<void> _run(ButtonWidgetConfig button) async {
    final path = _collectionPathFor(button.groupName);
    if (path == null) {
      setState(() => _resultText = '${button.groupName} has no collection endpoint to call.');
      return;
    }

    setState(() => _busy = true);
    ScreenActionResult result;
    switch (button.action) {
      case ScreenAction.list:
        result = await _client.list(widget.deploymentBase, path);
      case ScreenAction.create:
        result = await _client.create(widget.deploymentBase, path, _fieldValuesFor(button.groupName));
      case ScreenAction.update:
        final id = await _promptId('Update');
        if (id == null || id.trim().isEmpty) {
          setState(() => _busy = false);
          return;
        }
        result = await _client.update(widget.deploymentBase, path, id.trim(), _fieldValuesFor(button.groupName));
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
      appBar: AppBar(title: Text(widget.layout.name)),
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
      FieldWidgetConfig(:final groupName, :final fieldName) => SizedBox(
        width: 160,
        child: TextField(
          controller: _controllerFor('$groupName.$fieldName'),
          decoration: InputDecoration(labelText: fieldName),
        ),
      ),
      ButtonWidgetConfig() => FilledButton(
        onPressed: _busy ? null : () => _run(config),
        child: Text(config.action.name),
      ),
    };
  }
}

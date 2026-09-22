import 'package:flutter/material.dart';

import '../../api_connection/domain/api_discovery.dart';
import '../data/screen_action_client.dart';
import '../data/screen_layout_store.dart';
import '../domain/screen_layout.dart';
import '../domain/screen_widget_config.dart';
import 'autofocus_text_field.dart';
import 'runtime_screen_page.dart';

const _canvasHeight = 480.0;
const _defaultStep = 56.0;

/// A touch-driven, RAD-style screen designer (the user's own reference:
/// Delphi/RAD Studio's form designer) for one named screen. A screen is no
/// longer scoped to a single class — every `groups` entry is available, and
/// adding a Field or Button asks which class it binds to whenever there is
/// more than one, so one screen can mix widgets from several classes at
/// once. Tapping the palette places a widget (already configured through a
/// small dialog, rather than a separate blank-placeholder step); dragging a
/// placed widget repositions it; tapping a placed widget reopens that
/// dialog to rebind, retype or remove it. "Save" persists the layout
/// locally (`ScreenLayoutStore`) keyed by the screen's name; "Preview" runs
/// it for real against the connected backend (`RuntimeScreenPage`).
class ScreenDesignerPage extends StatefulWidget {
  const ScreenDesignerPage({
    super.key,
    required this.name,
    required this.groups,
    required this.deploymentBase,
    this.store = const ScreenLayoutStore(),
    this.actionClient,
  });

  final String name;
  final List<EndpointGroup> groups;
  final Uri deploymentBase;
  final ScreenLayoutStore store;
  final ScreenActionClient? actionClient;

  @override
  State<ScreenDesignerPage> createState() => _ScreenDesignerPageState();
}

class _ScreenDesignerPageState extends State<ScreenDesignerPage> {
  List<ScreenWidgetConfig> _widgets = const [];
  int _placedCount = 0;
  bool _loaded = false;
  bool _saving = false;

  bool get _multiClass => widget.groups.length > 1;

  @override
  void initState() {
    super.initState();
    widget.store.load(widget.name).then((layout) {
      if (!mounted) return;
      setState(() {
        _widgets = layout?.widgets ?? const [];
        _placedCount = _widgets.length;
        _loaded = true;
      });
    });
  }

  Offset _nextPosition() {
    final row = _placedCount ~/ 3;
    final col = _placedCount % 3;
    return Offset(16 + col * 130, 16 + row * _defaultStep);
  }

  /// Only asks when there is more than one class to choose from, so a
  /// single-class screen keeps its original, simpler add flow.
  Future<String?> _pickGroup({String? initial}) {
    if (!_multiClass) return Future.value(widget.groups.single.name);
    return _promptGroup(context, groups: widget.groups, initial: initial);
  }

  Future<void> _addLabel() async {
    final text = await _promptText(context, title: 'Add label', label: 'Text', initial: 'Label');
    if (text == null) return;
    final position = _nextPosition();
    setState(() {
      _placedCount++;
      _widgets = [
        ..._widgets,
        LabelWidgetConfig(id: _newId(), x: position.dx, y: position.dy, text: text),
      ];
    });
  }

  /// Offers a picker built from the class's real attribute names
  /// ([EndpointGroup.attributeNames], resolved from its OpenAPI request
  /// body schema) instead of the user typing one by hand, whenever the
  /// document exposed that shape; a class with no known attributes (e.g.
  /// read-only, or schema resolution failed) falls back to free text.
  Future<String?> _pickFieldName(String groupName, {String? initial, VoidCallback? onRemove}) {
    final attributes = widget.groups.firstWhere((g) => g.name == groupName).attributeNames;
    if (attributes.isEmpty) {
      return _promptText(
        context,
        title: initial == null ? 'Add field' : 'Edit field',
        label: 'Bound attribute name',
        initial: initial ?? '',
        onRemove: onRemove,
      );
    }
    return _promptAttribute(context, attributes: attributes, initial: initial, onRemove: onRemove);
  }

  Future<void> _addField() async {
    final groupName = await _pickGroup();
    if (groupName == null) return;
    if (!mounted) return;
    final fieldName = await _pickFieldName(groupName);
    if (fieldName == null || fieldName.trim().isEmpty) return;
    final position = _nextPosition();
    setState(() {
      _placedCount++;
      _widgets = [
        ..._widgets,
        FieldWidgetConfig(id: _newId(), x: position.dx, y: position.dy, groupName: groupName, fieldName: fieldName.trim()),
      ];
    });
  }

  Future<void> _addButton() async {
    final groupName = await _pickGroup();
    if (groupName == null) return;
    if (!mounted) return;
    final action = await _promptAction(context);
    if (action == null) return;
    final position = _nextPosition();
    setState(() {
      _placedCount++;
      _widgets = [
        ..._widgets,
        ButtonWidgetConfig(id: _newId(), x: position.dx, y: position.dy, groupName: groupName, action: action),
      ];
    });
  }

  void _move(String id, Offset delta) {
    setState(() {
      _widgets = [
        for (final w in _widgets)
          if (w.id == id) w.copyWith(x: w.x + delta.dx, y: w.y + delta.dy) else w,
      ];
    });
  }

  Future<void> _editOrRemove(ScreenWidgetConfig target) async {
    var removed = false;
    final ScreenWidgetConfig? edited;
    switch (target) {
      case LabelWidgetConfig(:final text):
        final newText = await _promptText(
          context,
          title: 'Edit label',
          label: 'Text',
          initial: text,
          onRemove: () => removed = true,
        );
        edited = newText == null ? null : target.copyWith(text: newText);
      case FieldWidgetConfig(:final groupName, :final fieldName):
        final newGroup = await _pickGroup(initial: groupName);
        if (newGroup == null) return;
        if (!mounted) return;
        final newName = await _pickFieldName(newGroup, initial: fieldName, onRemove: () => removed = true);
        edited = newName == null ? null : target.copyWith(groupName: newGroup, fieldName: newName.trim());
      case ButtonWidgetConfig(:final groupName):
        final newGroup = await _pickGroup(initial: groupName);
        if (newGroup == null) return;
        if (!mounted) return;
        final newAction = await _promptAction(context, initial: target.action, onRemove: () => removed = true);
        edited = newAction == null ? null : target.copyWith(groupName: newGroup, action: newAction);
    }
    if (!mounted) return;
    if (removed) {
      await _remove(target.id);
      return;
    }
    setState(() {
      _widgets = [
        for (final w in _widgets)
          if (w.id == target.id) (edited ?? w) else w,
      ];
    });
  }

  Future<void> _remove(String id) async {
    setState(() {
      _widgets = _widgets.where((w) => w.id != id).toList();
    });
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    await widget.store.save(ScreenLayout(name: widget.name, widgets: _widgets));
    if (!mounted) return;
    setState(() => _saving = false);
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Screen saved')));
  }

  void _preview() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => RuntimeScreenPage(
          layout: ScreenLayout(name: widget.name, widgets: _widgets),
          groups: widget.groups,
          deploymentBase: widget.deploymentBase,
          actionClient: widget.actionClient,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Design: ${widget.name}'),
        actions: [
          IconButton(
            icon: const Icon(Icons.play_arrow),
            tooltip: 'Preview',
            onPressed: _widgets.isEmpty ? null : _preview,
          ),
          IconButton(
            icon: _saving
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.save),
            tooltip: 'Save',
            onPressed: _saving ? null : _save,
          ),
        ],
      ),
      body: !_loaded
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                Padding(
                  padding: const EdgeInsets.all(8),
                  child: Wrap(
                    spacing: 8,
                    children: [
                      ActionChip(avatar: const Icon(Icons.text_fields, size: 18), label: const Text('Label'), onPressed: _addLabel),
                      ActionChip(avatar: const Icon(Icons.input, size: 18), label: const Text('Field'), onPressed: _addField),
                      ActionChip(avatar: const Icon(Icons.smart_button, size: 18), label: const Text('Button'), onPressed: _addButton),
                    ],
                  ),
                ),
                Expanded(
                  child: Container(
                    key: const Key('designer-canvas'),
                    margin: const EdgeInsets.all(8),
                    height: _canvasHeight,
                    decoration: BoxDecoration(border: Border.all(color: Theme.of(context).dividerColor)),
                    child: Stack(
                      children: [
                        for (final w in _widgets)
                          Positioned(
                            left: w.x,
                            top: w.y,
                            child: GestureDetector(
                              onPanUpdate: (details) => _move(w.id, details.delta),
                              onTap: () => _editOrRemove(w),
                              child: _PlacedWidgetChip(config: w, showGroup: _multiClass),
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
    );
  }
}

class _PlacedWidgetChip extends StatelessWidget {
  const _PlacedWidgetChip({required this.config, required this.showGroup});

  final ScreenWidgetConfig config;
  final bool showGroup;

  @override
  Widget build(BuildContext context) {
    final String text;
    final IconData icon;
    switch (config) {
      case LabelWidgetConfig(text: final labelText):
        text = labelText;
        icon = Icons.text_fields;
      case FieldWidgetConfig(groupName: final groupName, fieldName: final fieldName):
        text = showGroup ? 'Field: $fieldName ($groupName)' : 'Field: $fieldName';
        icon = Icons.input;
      case ButtonWidgetConfig(groupName: final groupName, action: final action):
        text = showGroup ? '${action.name} ($groupName)' : action.name;
        icon = Icons.smart_button;
    }
    return Card(
      color: Theme.of(context).colorScheme.secondaryContainer,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        child: Row(mainAxisSize: MainAxisSize.min, children: [Icon(icon, size: 16), const SizedBox(width: 4), Text(text)]),
      ),
    );
  }
}

String _newId() => DateTime.now().microsecondsSinceEpoch.toRadixString(36);

Future<String?> _promptText(
  BuildContext context, {
  required String title,
  required String label,
  required String initial,
  VoidCallback? onRemove,
}) {
  final controller = TextEditingController(text: initial);
  return showDialog<String>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: Text(title),
      content: AutofocusTextField(controller: controller, label: label),
      actions: [
        if (onRemove != null)
          TextButton(
            onPressed: () {
              onRemove();
              Navigator.of(dialogContext).pop();
            },
            child: const Text('Remove'),
          ),
        TextButton(onPressed: () => Navigator.of(dialogContext).pop(), child: const Text('Cancel')),
        FilledButton(
          onPressed: () => Navigator.of(dialogContext).pop(controller.text),
          child: const Text('Save'),
        ),
      ],
    ),
  );
}

Future<ScreenAction?> _promptAction(BuildContext context, {ScreenAction? initial, VoidCallback? onRemove}) {
  return showDialog<ScreenAction>(
    context: context,
    builder: (dialogContext) => SimpleDialog(
      title: const Text('Action'),
      children: [
        for (final action in ScreenAction.values)
          SimpleDialogOption(
            onPressed: () => Navigator.of(dialogContext).pop(action),
            child: Text(action.name),
          ),
        if (onRemove != null)
          SimpleDialogOption(
            onPressed: () {
              onRemove();
              Navigator.of(dialogContext).pop();
            },
            child: const Text('Remove'),
          ),
      ],
    ),
  );
}

/// Which class a Field/Button belongs to. Only shown when the screen has
/// more than one class available ([ScreenDesignerPage._multiClass]).
Future<String?> _promptGroup(BuildContext context, {required List<EndpointGroup> groups, String? initial}) {
  return showDialog<String>(
    context: context,
    builder: (dialogContext) => SimpleDialog(
      title: const Text('Class'),
      children: [
        for (final group in groups)
          SimpleDialogOption(
            onPressed: () => Navigator.of(dialogContext).pop(group.name),
            child: Text(group.name == initial ? '${group.name} (current)' : group.name),
          ),
      ],
    ),
  );
}

/// Which of the class's real attributes a Field binds to
/// ([EndpointGroup.attributeNames]) — used instead of free text whenever
/// the document exposed that class's request body shape.
Future<String?> _promptAttribute(
  BuildContext context, {
  required List<String> attributes,
  String? initial,
  VoidCallback? onRemove,
}) {
  return showDialog<String>(
    context: context,
    builder: (dialogContext) => SimpleDialog(
      title: const Text('Attribute'),
      children: [
        for (final attribute in attributes)
          SimpleDialogOption(
            onPressed: () => Navigator.of(dialogContext).pop(attribute),
            child: Text(attribute == initial ? '$attribute (current)' : attribute),
          ),
        if (onRemove != null)
          SimpleDialogOption(
            onPressed: () {
              onRemove();
              Navigator.of(dialogContext).pop();
            },
            child: const Text('Remove'),
          ),
      ],
    ),
  );
}

import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../domain/diagram_preview.dart';
import '../domain/organization.dart';
import 'session_controller.dart';
import 'widgets/remote_data.dart';

/// A small read-only picture of the diagram, so someone away from the PC can
/// follow its progress (GitHub #19). Pinch to zoom, drag to move. It never edits.
class DiagramPreviewTab extends StatefulWidget {
  const DiagramPreviewTab({super.key, required this.controller, required this.organization, required this.document});

  final SessionController controller;
  final Organization organization;
  final DocumentSummary document;

  @override
  State<DiagramPreviewTab> createState() => _DiagramPreviewTabState();
}

class _DiagramPreviewTabState extends State<DiagramPreviewTab> {
  final _data = GlobalKey<RemoteDataState<DiagramPreview>>();

  @override
  Widget build(BuildContext context) {
    return RemoteData<DiagramPreview>(
      key: _data,
      load: () => widget.controller.run((repository) => repository.getDiagram(widget.organization.slug, widget.document.id)),
      isEmpty: (preview) => preview.classes.isEmpty,
      emptyMessage: 'El diagrama todavía está vacío.',
      builder: (context, preview) => Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 4, 4, 0),
            child: Row(
              children: [
                Expanded(child: Text(_summary(preview), style: Theme.of(context).textTheme.bodyMedium)),
                IconButton(
                  tooltip: 'Actualizar',
                  icon: const Icon(Icons.refresh),
                  onPressed: () => _data.currentState?.refresh(),
                ),
              ],
            ),
          ),
          Expanded(child: _Canvas(preview: preview)),
        ],
      ),
    );
  }
}

String _summary(DiagramPreview preview) {
  final classes = preview.classes.length;
  final relationships = preview.relationships.length;
  return '$classes ${classes == 1 ? 'clase' : 'clases'} · '
      '$relationships ${relationships == 1 ? 'relación' : 'relaciones'}';
}

const double _cardWidth = 170;
const double _lineHeight = 16;
const double _headerHeight = 30;
const double _gap = 56;
const double _padding = 24;

double _cardHeight(PreviewClass item) {
  final members = item.attributes.length + item.operations.length;
  final divider = item.attributes.isNotEmpty && item.operations.isNotEmpty ? 6 : 0;
  return _headerHeight + 10 + members * _lineHeight + divider;
}

/// Where each class goes: its saved place on the web canvas, and the ones never
/// placed in a row underneath so nothing is hidden.
Map<String, Rect> _layout(DiagramPreview preview) {
  final rects = <String, Rect>{};
  final placed = [for (final item in preview.classes) if (item.x != null && item.y != null) item];
  final loose = [for (final item in preview.classes) if (item.x == null || item.y == null) item];

  for (final item in placed) {
    rects[item.id] = Rect.fromLTWH(item.x!, item.y!, _cardWidth, _cardHeight(item));
  }

  var top = placed.isEmpty ? 0.0 : rects.values.map((rect) => rect.bottom).reduce(math.max) + _gap;
  final columns = math.max(1, math.min(3, loose.length));
  var column = 0;
  var rowHeight = 0.0;
  var left = 0.0;
  for (final item in loose) {
    final height = _cardHeight(item);
    rects[item.id] = Rect.fromLTWH(left, top, _cardWidth, height);
    rowHeight = math.max(rowHeight, height);
    column++;
    left += _cardWidth + _gap;
    if (column == columns) {
      column = 0;
      left = 0;
      top += rowHeight + _gap;
      rowHeight = 0;
    }
  }

  if (rects.isEmpty) return rects;
  final minX = rects.values.map((rect) => rect.left).reduce(math.min);
  final minY = rects.values.map((rect) => rect.top).reduce(math.min);
  return {for (final entry in rects.entries) entry.key: entry.value.shift(Offset(_padding - minX, _padding - minY))};
}

class _Canvas extends StatefulWidget {
  const _Canvas({required this.preview});

  final DiagramPreview preview;

  @override
  State<_Canvas> createState() => _CanvasState();
}

class _CanvasState extends State<_Canvas> {
  final _transform = TransformationController();
  Size? _fittedFor;

  @override
  void dispose() {
    _transform.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final rects = _layout(widget.preview);
    final width = rects.values.map((rect) => rect.right).reduce(math.max) + _padding;
    final height = rects.values.map((rect) => rect.bottom).reduce(math.max) + _padding;
    final canvas = Size(width, height);

    return LayoutBuilder(
      builder: (context, box) {
        // Start zoomed out enough to see the whole diagram; the person can zoom in.
        if (_fittedFor != canvas) {
          _fittedFor = canvas;
          final scale = math.min(1.0, math.min(box.maxWidth / width, box.maxHeight / height));
          _transform.value = Matrix4.identity()..scaleByDouble(scale, scale, 1, 1);
        }
        return InteractiveViewer(
          transformationController: _transform,
          constrained: false,
          minScale: 0.2,
          maxScale: 3,
          boundaryMargin: const EdgeInsets.all(200),
          child: SizedBox(
            width: width,
            height: height,
            child: Stack(
              children: [
                Positioned.fill(
                  child: CustomPaint(
                    painter: _RelationshipPainter(
                      relationships: widget.preview.relationships,
                      rects: rects,
                      color: Theme.of(context).colorScheme.outline,
                      textColor: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                ),
                for (final item in widget.preview.classes)
                  Positioned.fromRect(rect: rects[item.id]!, child: _ClassCard(item: item)),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _ClassCard extends StatelessWidget {
  const _ClassCard({required this.item});

  final PreviewClass item;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    const memberStyle = TextStyle(fontSize: 11, height: 1.3, fontFamily: 'monospace');
    return DecoratedBox(
      decoration: BoxDecoration(
        color: scheme.surface,
        border: Border.all(color: scheme.outline),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            height: _headerHeight,
            width: double.infinity,
            alignment: Alignment.center,
            padding: const EdgeInsets.symmetric(horizontal: 6),
            decoration: BoxDecoration(color: scheme.primaryContainer, borderRadius: const BorderRadius.vertical(top: Radius.circular(3))),
            child: Text(
              item.name,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontWeight: FontWeight.w600,
                fontStyle: item.isAbstract ? FontStyle.italic : FontStyle.normal,
                color: scheme.onPrimaryContainer,
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(6, 5, 6, 0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final line in item.attributes) _Member(text: line, style: memberStyle),
                if (item.attributes.isNotEmpty && item.operations.isNotEmpty)
                  SizedBox(height: 6, child: Divider(height: 6, color: scheme.outlineVariant)),
                for (final line in item.operations) _Member(text: line, style: memberStyle),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Member extends StatelessWidget {
  const _Member({required this.text, required this.style});

  final String text;
  final TextStyle style;

  @override
  Widget build(BuildContext context) =>
      SizedBox(height: _lineHeight, child: Text(text, maxLines: 1, overflow: TextOverflow.ellipsis, style: style));
}

class _RelationshipPainter extends CustomPainter {
  _RelationshipPainter({required this.relationships, required this.rects, required this.color, required this.textColor});

  final List<PreviewRelationship> relationships;
  final Map<String, Rect> rects;
  final Color color;
  final Color textColor;

  @override
  void paint(Canvas canvas, Size size) {
    final stroke = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    for (final relationship in relationships) {
      final from = rects[relationship.sourceId];
      final to = rects[relationship.targetId];
      if (from == null || to == null) continue;
      // A class related to itself has no line to draw between two boxes.
      if (relationship.sourceId == relationship.targetId) continue;

      final start = _edge(from, to.center);
      final end = _edge(to, from.center);
      if (relationship.kind == RelationshipKind.dependency) {
        _dashedLine(canvas, start, end, stroke);
      } else {
        canvas.drawLine(start, end, stroke);
      }
      _decorate(canvas, relationship.kind, start, end, stroke);
      if (relationship.kind.hasMultiplicity) {
        _label(canvas, relationship.sourceMultiplicity, start, end);
        _label(canvas, relationship.targetMultiplicity, end, start);
      }
      if (relationship.name.isNotEmpty) _label(canvas, relationship.name, (start + end) / 2, (start + end) / 2, middle: true);
    }
  }

  // A dashed line: 7 px drawn, 5 px skipped (UML draws a dependency this way).
  void _dashedLine(Canvas canvas, Offset start, Offset end, Paint paint) {
    final length = (end - start).distance;
    if (length == 0) return;
    final direction = (end - start) / length;
    for (var travelled = 0.0; travelled < length; travelled += 12) {
      final from = start + direction * travelled;
      final to = start + direction * math.min(travelled + 7, length);
      canvas.drawLine(from, to, paint);
    }
  }

  // Where the line from a box's center towards `toward` leaves the box.
  Offset _edge(Rect rect, Offset toward) {
    final center = rect.center;
    final delta = toward - center;
    if (delta == Offset.zero) return center;
    final scaleX = delta.dx == 0 ? double.infinity : (rect.width / 2) / delta.dx.abs();
    final scaleY = delta.dy == 0 ? double.infinity : (rect.height / 2) / delta.dy.abs();
    return center + delta * math.min(scaleX, scaleY);
  }

  void _decorate(Canvas canvas, RelationshipKind kind, Offset start, Offset end, Paint stroke) {
    final fill = Paint()..color = kind == RelationshipKind.composition ? color : Colors.white;
    switch (kind) {
      case RelationshipKind.association:
        break;
      case RelationshipKind.dependency:
        // An open arrow at the supplier: two strokes forming a "V".
        final direction = (start - end) / (start - end).distance;
        final normal = Offset(-direction.dy, direction.dx);
        final base = end + direction * 12;
        canvas.drawLine(end, base + normal * 7, stroke);
        canvas.drawLine(end, base - normal * 7, stroke);
      case RelationshipKind.generalization:
        canvas.drawPath(_arrowHead(end, start, 12, 7), fill);
        canvas.drawPath(_arrowHead(end, start, 12, 7), stroke);
      case RelationshipKind.aggregation || RelationshipKind.composition:
        canvas.drawPath(_diamond(start, end, 16, 6), fill);
        canvas.drawPath(_diamond(start, end, 16, 6), stroke);
    }
  }

  // A triangle whose tip is at `tip`, pointing away from `from`.
  Path _arrowHead(Offset tip, Offset from, double length, double half) {
    final direction = (from - tip) / (from - tip).distance;
    final normal = Offset(-direction.dy, direction.dx);
    final base = tip + direction * length;
    return Path()
      ..moveTo(tip.dx, tip.dy)
      ..lineTo((base + normal * half).dx, (base + normal * half).dy)
      ..lineTo((base - normal * half).dx, (base - normal * half).dy)
      ..close();
  }

  Path _diamond(Offset tip, Offset towards, double length, double half) {
    final direction = (towards - tip) / (towards - tip).distance;
    final normal = Offset(-direction.dy, direction.dx);
    final middle = tip + direction * (length / 2);
    final far = tip + direction * length;
    return Path()
      ..moveTo(tip.dx, tip.dy)
      ..lineTo((middle + normal * half).dx, (middle + normal * half).dy)
      ..lineTo(far.dx, far.dy)
      ..lineTo((middle - normal * half).dx, (middle - normal * half).dy)
      ..close();
  }

  void _label(Canvas canvas, String text, Offset near, Offset towards, {bool middle = false}) {
    if (text.isEmpty) return;
    final painter = TextPainter(
      text: TextSpan(text: text, style: TextStyle(fontSize: 10, color: textColor)),
      textDirection: TextDirection.ltr,
    )..layout();
    var at = near;
    if (!middle) {
      final delta = towards - near;
      final direction = delta.distance == 0 ? Offset.zero : delta / delta.distance;
      at = near + direction * 20 + Offset(-direction.dy, direction.dx) * 10;
    }
    painter.paint(canvas, at - Offset(painter.width / 2, painter.height / 2));
  }

  @override
  bool shouldRepaint(_RelationshipPainter old) =>
      old.relationships != relationships || old.rects != rects || old.color != color;
}

import type { TemplatePreview } from "@/lib/uml_documents";

const BOX_WIDTH = 120;
const BOX_HEIGHT = 44;
const PADDING = 16;

/**
 * Presentational thumbnail of a template: one box per class at its saved
 * position, one line per relationship. Purely derived from `preview`, so it
 * needs no image storage and always matches the template's content.
 */
export function TemplatePreviewThumbnail({ preview }: { preview: TemplatePreview }) {
  if (preview.classes.length === 0) {
    return (
      <div className="flex h-28 items-center justify-center rounded-md bg-muted/40 text-xs text-muted-foreground">
        Plantilla vacía
      </div>
    );
  }

  const minX = Math.min(...preview.classes.map((item) => item.x)) - PADDING;
  const minY = Math.min(...preview.classes.map((item) => item.y)) - PADDING;
  const maxX = Math.max(...preview.classes.map((item) => item.x)) + BOX_WIDTH + PADDING;
  const maxY = Math.max(...preview.classes.map((item) => item.y)) + BOX_HEIGHT + PADDING;
  const byId = new Map(preview.classes.map((item) => [item.id, item]));

  return (
    <svg
      viewBox={`${minX} ${minY} ${maxX - minX} ${maxY - minY}`}
      className="h-28 w-full rounded-md bg-muted/40"
      aria-hidden="true"
      data-testid="template-thumbnail"
    >
      {preview.relationships.map((relationship, index) => {
        const source = byId.get(relationship.source);
        const target = byId.get(relationship.target);
        if (!source || !target) return null;
        return (
          <line
            key={`${relationship.source}-${relationship.target}-${index}`}
            x1={source.x + BOX_WIDTH / 2}
            y1={source.y + BOX_HEIGHT / 2}
            x2={target.x + BOX_WIDTH / 2}
            y2={target.y + BOX_HEIGHT / 2}
            stroke="currentColor"
            strokeWidth={3}
            className="text-muted-foreground"
          />
        );
      })}
      {preview.classes.map((item) => (
        <g key={item.id}>
          <rect
            x={item.x}
            y={item.y}
            width={BOX_WIDTH}
            height={BOX_HEIGHT}
            rx={6}
            className="fill-card stroke-border"
            strokeWidth={3}
          />
          <text
            x={item.x + BOX_WIDTH / 2}
            y={item.y + BOX_HEIGHT / 2 + 6}
            textAnchor="middle"
            fontSize={18}
            fontWeight={600}
            className="fill-foreground"
          >
            {item.name.length > 12 ? `${item.name.slice(0, 11)}…` : item.name}
          </text>
        </g>
      ))}
    </svg>
  );
}

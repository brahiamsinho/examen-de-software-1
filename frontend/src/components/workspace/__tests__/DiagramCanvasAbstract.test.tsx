import { describe, expect, it } from "vitest";

import { toElements } from "@/components/workspace/DiagramCanvas";
import type { UmlModel } from "@/lib/uml_documents";

function svgOf(model: UmlModel, id: string): string {
  const node = toElements(model).find((element) => element.data.id === id)!;
  return decodeURIComponent((node.data.bgImage as string).replace("data:image/svg+xml,", ""));
}

const model: UmlModel = {
  classes: [
    { id: "c1", name: "Forma", visibility: "public", attributes: [], operations: [], is_abstract: true },
    { id: "c2", name: "Pedido", visibility: "public", attributes: [], operations: [] },
  ],
  enumerations: [],
  relationships: [],
  generation_metadata: {},
};

// UML 2.5 writes the name of an abstract class in italics.
describe("an abstract class on the canvas", () => {
  it("has its name in italics", () => {
    expect(svgOf(model, "c1")).toMatch(/<text[^>]*font-style="italic"[^>]*>Forma<\/text>/);
  });

  it("does not italicize a concrete class, or one saved before the flag existed", () => {
    expect(svgOf(model, "c2")).not.toContain("italic");
  });

  it("keeps the same box size as a concrete class with the same content", () => {
    const abstract = toElements(model).find((element) => element.data.id === "c1")!;
    const concrete = toElements({
      ...model,
      classes: [{ ...model.classes[0], is_abstract: false }],
    }).find((element) => element.data.id === "c1")!;

    expect([abstract.data.width, abstract.data.height]).toEqual([concrete.data.width, concrete.data.height]);
  });
});

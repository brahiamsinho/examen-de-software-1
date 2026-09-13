import * as React from "react";
import { ChevronDown } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * Styled wrapper around a real native `<select>` — not a Base UI listbox.
 * Deliberate: a custom popover-based select would change how RTL queries
 * it (`fireEvent.change` + `getByLabelText` no longer apply), forcing a
 * rewrite of every existing control test for a visual-only change. A
 * well-styled native select is a normal, professional pattern and keeps
 * every existing test's interaction model unchanged.
 */
function Select({ className, children, ...props }: React.ComponentProps<"select">) {
  return (
    <div className="relative">
      <select
        data-slot="select"
        className={cn(
          "flex h-9 w-full min-w-0 appearance-none rounded-lg border border-input bg-background px-3 py-1 pr-8 text-sm text-foreground shadow-xs transition-[color,box-shadow] outline-none",
          "focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50",
          "disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50",
          className,
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDown className="pointer-events-none absolute top-1/2 right-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
    </div>
  );
}

export { Select };

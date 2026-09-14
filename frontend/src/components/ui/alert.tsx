import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const alertVariants = cva(
  "flex items-start gap-2.5 rounded-lg border p-3 text-sm [&_svg]:mt-0.5 [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "border-border bg-muted text-foreground [&_svg]:text-muted-foreground",
        destructive: "border-destructive/30 bg-destructive/10 text-destructive [&_svg]:text-destructive",
        caution: "border-caution/30 bg-caution/10 text-caution-foreground [&_svg]:text-caution",
        success: "border-success/30 bg-success/10 text-success-foreground [&_svg]:text-success",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

function Alert({
  className,
  variant,
  ...props
}: React.ComponentProps<"div"> & VariantProps<typeof alertVariants>) {
  return (
    <div data-slot="alert" role="alert" className={cn(alertVariants({ variant }), className)} {...props} />
  );
}

function AlertDescription({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="alert-description"
      className={cn("flex flex-col gap-0.5 [&_p]:leading-relaxed", className)}
      {...props}
    />
  );
}

export { Alert, AlertDescription };

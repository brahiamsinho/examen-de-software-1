import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { NavLogo } from "@/components/landing/NavLogo";
import { brandGradient } from "@/components/landing/gradients";

const navLinks = [
  { href: "#producto", label: "Producto" },
  { href: "#organizaciones", label: "Organizaciones" },
  { href: "#precios", label: "Precios" },
];

export function Navbar() {
  return (
    <header className="sticky top-0 z-20 flex justify-center border-b border-border bg-background/85 backdrop-blur">
      <div className="flex w-full max-w-[1160px] flex-wrap items-center justify-between gap-6 px-6 py-4">
        <div className="flex items-center gap-[10px]">
          <NavLogo />
          <span className="font-heading text-lg font-bold tracking-tight">Modelia</span>
        </div>

        <nav className="flex items-center gap-7 text-sm font-semibold text-muted-foreground">
          {navLinks.map((link) => (
            <a key={link.href} href={link.href} className="hover:text-foreground">
              {link.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-[10px]">
          <a href="#" className={cn(buttonVariants({ variant: "ghost" }), "h-auto px-[14px] py-2")}>
            Iniciar sesión
          </a>
          <a
            href="#precios"
            className={cn(
              buttonVariants({ variant: "default" }),
              brandGradient,
              "h-auto border-0 px-[18px] py-2 text-white shadow-[0_6px_16px_-6px_color-mix(in_oklch,var(--primary)_60%,transparent)]"
            )}
          >
            Empezar gratis
          </a>
        </div>
      </div>
    </header>
  );
}

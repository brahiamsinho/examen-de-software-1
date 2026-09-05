import { NavLogo } from "@/components/landing/NavLogo";

const links = [
  { href: "#producto", label: "Producto" },
  { href: "#organizaciones", label: "Organizaciones" },
  { href: "#precios", label: "Precios" },
];

export function Footer() {
  return (
    <footer className="flex justify-center border-t border-border px-6 py-8">
      <div className="flex w-full max-w-[1160px] flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <NavLogo size={20} />
          <span className="text-[13.5px] font-semibold text-muted-foreground">
            © 2026 Modelia
          </span>
        </div>
        <nav className="flex gap-[22px] text-[13.5px] font-semibold text-muted-foreground">
          {links.map((link) => (
            <a key={link.href} href={link.href} className="hover:text-foreground">
              {link.label}
            </a>
          ))}
        </nav>
      </div>
    </footer>
  );
}

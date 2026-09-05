import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { brandGradient, heroMeshGradientA, heroMeshGradientB } from "@/components/landing/gradients";

function OrgProjectDiagram() {
  return (
    <svg viewBox="0 0 420 300" width="100%" height="auto" className="block" aria-hidden="true">
      <rect x="14" y="18" width="168" height="128" rx="12" fill="var(--card)" stroke="var(--border)" strokeWidth="1.5" />
      <rect x="14" y="18" width="168" height="34" rx="12" fill="var(--accent)" />
      <text x="98" y="40" textAnchor="middle" className="font-heading" fontSize="13" fontWeight="700" fill="var(--foreground)">
        Organization
      </text>
      <line x1="14" y1="52" x2="182" y2="52" stroke="var(--border)" />
      <text x="24" y="72" fontSize="11" fill="var(--muted-foreground)">+ id: UUID</text>
      <text x="24" y="90" fontSize="11" fill="var(--muted-foreground)">+ name: String</text>
      <text x="24" y="108" fontSize="11" fill="var(--muted-foreground)">+ plan: PlanTier</text>
      <text x="24" y="126" fontSize="11" fill="var(--muted-foreground)">+ members: Member[]</text>

      <rect x="238" y="140" width="168" height="128" rx="12" fill="var(--card)" stroke="var(--border)" strokeWidth="1.5" />
      <rect x="238" y="140" width="168" height="34" rx="12" fill="color-mix(in oklch, #2563eb 14%, white)" />
      <text x="322" y="162" textAnchor="middle" className="font-heading" fontSize="13" fontWeight="700" fill="var(--foreground)">
        Project
      </text>
      <line x1="238" y1="174" x2="406" y2="174" stroke="var(--border)" />
      <text x="248" y="194" fontSize="11" fill="var(--muted-foreground)">+ id: UUID</text>
      <text x="248" y="212" fontSize="11" fill="var(--muted-foreground)">+ name: String</text>
      <text x="248" y="230" fontSize="11" fill="var(--muted-foreground)">+ updatedAt: DateTime</text>
      <text x="248" y="248" fontSize="11" fill="var(--muted-foreground)">+ model: CanonicalUmlModel</text>

      <path d="M98 146 C 140 190, 170 190, 236 204" stroke="var(--primary)" strokeWidth="1.6" fill="none" />
      <circle cx="98" cy="146" r="4" fill="var(--primary)" />
      <text x="108" y="168" fontSize="11" fontWeight="700" fill="var(--primary)">1</text>
      <text x="214" y="200" fontSize="11" fontWeight="700" fill="var(--primary)">*</text>
    </svg>
  );
}

export function Hero() {
  return (
    <section className="relative flex justify-center overflow-hidden px-6 pt-20 pb-24">
      <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden">
        <div className={cn("absolute -top-40 -left-30 h-[520px] w-[520px] rounded-full blur-[10px]", heroMeshGradientA)} />
        <div className={cn("absolute -top-20 -right-40 h-[560px] w-[560px] rounded-full blur-[10px]", heroMeshGradientB)} />
      </div>

      <div className="relative z-10 grid w-full max-w-[1160px] grid-cols-1 items-center gap-14 md:grid-cols-2">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-[14px] py-[6px] text-sm font-bold text-accent-foreground shadow-sm">
            <span className="h-[6px] w-[6px] rounded-full bg-primary" />
            Multi-organización · Tiempo real · IA
          </div>

          <h1 className="mt-5 text-[clamp(2.1rem,4.6vw,3.25rem)] leading-[1.06] tracking-tight font-heading">
            Un modelo UML, una sola verdad — para toda tu organización.
          </h1>

          <p className="mt-5 max-w-[520px] text-lg leading-relaxed text-muted-foreground">
            Modelia es el CASE tool donde tus equipos modelan, colaboran y generan código a partir
            de un único modelo canónico. Cada organización con sus propios proyectos, miembros y
            permisos — sin archivos sueltos ni versiones que no coinciden.
          </p>

          <div className="mt-8 flex flex-wrap gap-[14px]">
            <a
              href="#precios"
              className={cn(
                buttonVariants({ variant: "default" }),
                brandGradient,
                "h-auto border-0 px-6 py-[14px] text-base text-white shadow-[0_10px_24px_-10px_color-mix(in_oklch,var(--primary)_65%,transparent)]"
              )}
            >
              Empezar gratis
            </a>
            <a
              href="#producto"
              className={cn(buttonVariants({ variant: "outline" }), "h-auto px-6 py-[14px] text-base")}
            >
              Ver cómo funciona
            </a>
          </div>

          <p className="mt-[14px] text-sm text-muted-foreground">
            Sin tarjeta de crédito · Cancelás cuando quieras
          </p>
        </div>

        <div>
          <div className="rounded-[20px] border border-border bg-card p-5 shadow-[0_24px_60px_-24px_rgba(30,20,70,0.22)]">
            <OrgProjectDiagram />
            <div className="mt-[14px] flex items-center gap-2 border-t border-border pt-[14px]">
              <span className="h-2 w-2 rounded-full bg-green-500" />
              <span className="text-xs font-semibold text-muted-foreground">
                3 personas editando este modelo ahora
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

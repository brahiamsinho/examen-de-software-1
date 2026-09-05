import { Check } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { brandGradient } from "@/components/landing/gradients";

type Plan = {
  name: string;
  price: string;
  priceSuffix?: string;
  pitch: string;
  perks: string[];
  cta: string;
  highlighted?: boolean;
};

const plans: Plan[] = [
  {
    name: "Starter",
    price: "$0",
    priceSuffix: "/mes",
    pitch: "Para probar Modelia con un equipo chico.",
    perks: [
      "1 organización",
      "Hasta 3 miembros",
      "2 proyectos activos",
      "Modelado manual + exportación básica",
    ],
    cta: "Empezar gratis",
  },
  {
    name: "Team",
    price: "[PRECIO]",
    priceSuffix: "/org · mes",
    pitch: "Para organizaciones que colaboran todos los días.",
    perks: [
      "Organizaciones y miembros ilimitados",
      "Colaboración en tiempo real",
      "Generación de código completa",
      "Asistente con IA",
      "Importación de imagen, voz y XMI",
    ],
    cta: "Elegir Team",
    highlighted: true,
  },
  {
    name: "Enterprise",
    price: "Hablemos",
    pitch: "Para instituciones y organizaciones grandes.",
    perks: [
      "Todo lo de Team",
      "SSO y roles avanzados",
      "Soporte dedicado + SLA",
      "Auditoría entre organizaciones",
    ],
    cta: "Contactar ventas",
  },
];

export function Pricing() {
  return (
    <section id="precios" className="flex justify-center px-6 pb-25">
      <div className="w-full max-w-[1160px]">
        <div className="mx-auto mb-12 max-w-[600px] text-center">
          <h2 className="text-[clamp(1.65rem,3vw,2.125rem)] tracking-tight font-heading">
            Planes para cada etapa de tu equipo
          </h2>
          <p className="mt-3 text-base leading-relaxed text-muted-foreground">
            Empezá gratis y escalá cuando tu organización crezca.
          </p>
        </div>

        <div className="grid grid-cols-1 items-stretch gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={cn(
                "relative flex flex-col rounded-[18px] border bg-card p-8",
                plan.highlighted
                  ? "scale-102 border-2 border-primary shadow-[0_20px_44px_-20px_color-mix(in_oklch,var(--primary)_45%,transparent)]"
                  : "border-border"
              )}
            >
              {plan.highlighted && (
                <div
                  className={cn(
                    "absolute -top-[14px] left-1/2 -translate-x-1/2 rounded-full px-[14px] py-[6px] text-[11.5px] font-bold whitespace-nowrap text-white",
                    brandGradient
                  )}
                >
                  Más elegido
                </div>
              )}

              <h3
                className={cn(
                  "text-base font-bold",
                  plan.highlighted ? "text-primary" : "text-muted-foreground"
                )}
              >
                {plan.name}
              </h3>

              <div className="mt-3 flex items-baseline gap-[6px]">
                <span className="font-heading text-[2.375rem] font-bold">{plan.price}</span>
                {plan.priceSuffix && (
                  <span className="text-sm text-muted-foreground">{plan.priceSuffix}</span>
                )}
              </div>
              <p className="mt-[6px] text-[13.5px] text-muted-foreground">{plan.pitch}</p>

              <div className="my-[22px] h-px bg-border" />

              <div className="flex flex-1 flex-col gap-3">
                {plan.perks.map((perk) => (
                  <span key={perk} className="flex items-center gap-2 text-[13.5px]">
                    <Check className="h-[14px] w-[14px] shrink-0 text-primary" strokeWidth={2.4} />
                    {perk}
                  </span>
                ))}
              </div>

              <a
                href="#"
                className={cn(
                  buttonVariants({ variant: plan.highlighted ? "default" : "outline" }),
                  "mt-6 h-auto justify-center py-3 text-[14.5px]",
                  plan.highlighted
                    ? cn(brandGradient, "border-0 text-white")
                    : "border-border bg-muted/60 hover:bg-muted"
                )}
              >
                {plan.cta}
              </a>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

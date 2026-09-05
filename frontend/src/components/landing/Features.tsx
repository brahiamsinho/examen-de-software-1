import { Boxes, Code2, Sparkles, Waypoints } from "lucide-react";
import type { LucideIcon } from "lucide-react";

type Feature = {
  icon: LucideIcon;
  title: string;
  description: string;
};

const features: Feature[] = [
  {
    icon: Boxes,
    title: "Modelo canónico único",
    description:
      "Cada diagrama, exportación y línea de código generada parte del mismo modelo. Cambiás una vez y se refleja en todos lados.",
  },
  {
    icon: Waypoints,
    title: "Cuatro formas de modelar",
    description:
      "Dibujá a mano, subí una foto de un diagrama, dictalo por voz o importá un XMI existente. Todo converge al mismo modelo.",
  },
  {
    icon: Code2,
    title: "Generación de código",
    description:
      "Exportá a Spring Boot y a tu esquema relacional con un clic, directo desde el modelo ya validado.",
  },
  {
    icon: Sparkles,
    title: "Asistente con IA",
    description:
      "Pedile cambios en lenguaje natural: arma un plan corto y lo aplica sobre el modelo, con vos revisando cada paso.",
  },
];

export function Features() {
  return (
    <section id="producto" className="flex justify-center px-6 pt-6 pb-22">
      <div className="w-full max-w-[1160px]">
        <div className="mx-auto mb-12 max-w-[640px] text-center">
          <h2 className="text-[clamp(1.65rem,3vw,2.125rem)] tracking-tight font-heading">
            Todo lo que necesita tu equipo, en un solo lugar
          </h2>
          <p className="mt-3 text-base leading-relaxed text-muted-foreground">
            Del primer boceto al código en producción, sin salir del modelo.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {features.map(({ icon: Icon, title, description }) => (
            <div key={title} className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <div className="flex h-10 w-10 items-center justify-center rounded-[11px] bg-accent">
                <Icon className="h-5 w-5 text-accent-foreground" strokeWidth={1.8} />
              </div>
              <h3 className="mt-4 text-[16.5px] font-semibold font-heading">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

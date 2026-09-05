import { Check } from "lucide-react";
import { avatarGradient } from "@/components/landing/gradients";
import { cn } from "@/lib/utils";

const bullets = [
  "Organizaciones y miembros ilimitados en los planes pagos",
  "Roles por miembro: owner, editor y lector",
  "Aislamiento total de datos entre organizaciones",
];

const members = [
  { initials: "MB", name: "María B.", role: "Owner", gradient: avatarGradient },
  {
    initials: "JL",
    name: "Juan L.",
    role: "Editor",
    gradient: "bg-[linear-gradient(135deg,#f59e0b,#ef4444)]",
  },
  {
    initials: "RS",
    name: "Rocío S.",
    role: "Lector",
    gradient: "bg-[linear-gradient(135deg,#14b8a6,#22c55e)]",
  },
];

export function Organizations() {
  return (
    <section id="organizaciones" className="flex justify-center px-6 pb-24">
      <div className="grid w-full max-w-[1160px] grid-cols-1 items-center gap-14 rounded-3xl border border-border bg-card p-12 md:grid-cols-2">
        <div>
          <h2 className="text-[clamp(1.5rem,2.8vw,1.875rem)] leading-[1.15] tracking-tight font-heading">
            Pensado para organizaciones, no solo para proyectos sueltos
          </h2>
          <p className="mt-4 text-[15.5px] leading-relaxed text-muted-foreground">
            Cada organización tiene sus propios proyectos, miembros y roles. Invitá a tu equipo,
            asignales permisos y trabajen juntos sobre el mismo modelo en tiempo real — sin
            pisarse entre organizaciones ni entre proyectos.
          </p>
          <div className="mt-6 flex flex-col gap-[14px]">
            {bullets.map((bullet) => (
              <div key={bullet} className="flex items-start gap-[10px]">
                <Check className="mt-[2px] h-[18px] w-[18px] shrink-0 text-primary" strokeWidth={2.2} />
                <span className="text-sm text-foreground/85">{bullet}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-background p-6">
          <div className="mb-4 flex items-center justify-between">
            <span className="text-xs font-bold tracking-wide text-muted-foreground uppercase">
              Tu organización
            </span>
            <span className="rounded-full bg-accent px-[10px] py-1 text-[11.5px] font-bold text-accent-foreground">
              Plan Team
            </span>
          </div>
          <div className="flex flex-col gap-[10px]">
            {members.map((member) => (
              <div
                key={member.initials}
                className="flex items-center justify-between rounded-[11px] border border-border bg-card px-[14px] py-3"
              >
                <div className="flex items-center gap-[10px]">
                  <div
                    className={cn(
                      "flex h-[30px] w-[30px] items-center justify-center rounded-full text-xs font-bold text-white",
                      member.gradient
                    )}
                  >
                    {member.initials}
                  </div>
                  <span className="text-[13.5px] font-semibold">{member.name}</span>
                </div>
                <span className="text-xs font-semibold text-muted-foreground">{member.role}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

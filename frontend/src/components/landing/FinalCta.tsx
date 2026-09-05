import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { ctaBandGradient } from "@/components/landing/gradients";

export function FinalCta() {
  return (
    <section className="flex justify-center px-6 pb-24">
      <div
        className={cn(
          "w-full max-w-[1160px] rounded-3xl px-10 py-14 text-center",
          ctaBandGradient
        )}
      >
        <h2 className="text-[clamp(1.5rem,3vw,2rem)] tracking-tight text-white font-heading">
          Tu equipo ya tiene el modelo en la cabeza.
        </h2>
        <p className="mt-[10px] text-base text-white/82">
          Ponelo en Modelia y dejá que todos trabajen sobre la misma verdad.
        </p>
        <a
          href="#"
          className={cn(
            buttonVariants({ variant: "default" }),
            "mt-[26px] h-auto border-0 bg-white px-[26px] py-[14px] text-base text-primary hover:bg-white/90"
          )}
        >
          Empezar gratis — sin tarjeta
        </a>
      </div>
    </section>
  );
}

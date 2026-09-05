import { Navbar } from "@/components/landing/Navbar";
import { Hero } from "@/components/landing/Hero";
import { Features } from "@/components/landing/Features";
import { Organizations } from "@/components/landing/Organizations";
import { Pricing } from "@/components/landing/Pricing";
import { FinalCta } from "@/components/landing/FinalCta";
import { Footer } from "@/components/landing/Footer";

export default function Home() {
  return (
    <div className="min-h-full overflow-x-hidden">
      <Navbar />
      <Hero />
      <Features />
      <Organizations />
      <Pricing />
      <FinalCta />
      <Footer />
    </div>
  );
}

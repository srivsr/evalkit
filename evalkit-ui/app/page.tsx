import { Hero } from "@/components/landing/Hero";
import { FeatureGrid } from "@/components/landing/FeatureGrid";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { MetricsPreview } from "@/components/landing/MetricsPreview";
import { Footer } from "@/components/Footer";

export default function Home() {
  return (
    <main className="min-h-screen">
      <Hero />
      <FeatureGrid />
      <HowItWorks />
      <MetricsPreview />
      <Footer />
    </main>
  );
}

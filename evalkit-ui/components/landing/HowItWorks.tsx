import { Upload, Cpu, CheckCircle } from "lucide-react";

const steps = [
  {
    icon: Upload,
    title: "Send",
    description: "Submit query, response, and retrieved contexts to the API.",
  },
  {
    icon: Cpu,
    title: "Evaluate",
    description: "6-layer pipeline runs: retrieval, claims, generation, root cause, anomalies.",
  },
  {
    icon: CheckCircle,
    title: "Fix",
    description: "Get verdict, root cause diagnosis, and prioritized fix suggestions.",
  },
];

export function HowItWorks() {
  return (
    <section className="py-20 px-4 bg-slate-900/30">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-3xl font-bold text-center mb-12">How It Works</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {steps.map((step, i) => (
            <div key={step.title} className="text-center">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-emerald-500/10 border border-emerald-500/20 mb-4">
                <step.icon className="text-emerald-400" size={24} />
              </div>
              <div className="text-xs text-slate-500 font-mono mb-2">
                STEP {i + 1}
              </div>
              <h3 className="text-lg font-semibold mb-2">{step.title}</h3>
              <p className="text-sm text-slate-400">{step.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

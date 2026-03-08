import {
  Search, Brain, FileCheck, AlertTriangle, GitCompare, Wrench,
} from "lucide-react";

const features = [
  {
    icon: Search,
    title: "Layer A: Retrieval Metrics",
    description: "Precision@K, Recall@K, NDCG, MRR, Hit Rate — classical IR metrics calculated from relevance labels.",
    color: "text-blue-400",
  },
  {
    icon: Brain,
    title: "Layer B: Generation Quality",
    description: "LLM-as-judge for faithfulness and answer relevance. Multi-judge consensus with agreement tracking.",
    color: "text-purple-400",
  },
  {
    icon: FileCheck,
    title: "Layer C: Claim Verification",
    description: "Every claim decomposed and mapped to evidence spans. Fuzzy matching with support classification.",
    color: "text-emerald-400",
  },
  {
    icon: AlertTriangle,
    title: "Layer D: Root Cause Cascade",
    description: "17 failure codes with deterministic 6-step cascade. Severity mapping from blocker to none.",
    color: "text-red-400",
  },
  {
    icon: GitCompare,
    title: "Anomaly Detection",
    description: "5 cross-metric contradiction rules. Catches when metrics disagree, indicating evaluation issues.",
    color: "text-amber-400",
  },
  {
    icon: Wrench,
    title: "Fix Suggestions",
    description: "Actionable remediation for each root cause. Prioritized by severity with specific targets.",
    color: "text-cyan-400",
  },
];

export function FeatureGrid() {
  return (
    <section className="py-20 px-4 max-w-6xl mx-auto">
      <h2 className="text-3xl font-bold text-center mb-4">6-Layer Evaluation Pipeline</h2>
      <p className="text-slate-400 text-center mb-12 max-w-2xl mx-auto">
        Not just a score — a complete diagnosis of what went wrong and why.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {features.map((feature) => (
          <div
            key={feature.title}
            className="bg-slate-900/50 border border-slate-800 rounded-lg p-6 hover:border-slate-700 transition-colors"
          >
            <feature.icon className={`${feature.color} mb-4`} size={28} />
            <h3 className="font-semibold text-lg mb-2">{feature.title}</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              {feature.description}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

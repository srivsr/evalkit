"use client";
import { cn } from "@/lib/utils";
import { Check, X, ChevronRight } from "lucide-react";
import { CASCADE_STEPS } from "@/lib/constants";

interface CascadeVizProps {
  rootCauseCode: string;
  attribution: string;
}

function getStepStatus(
  stepId: number,
  rootCauseCode: string,
): "pass" | "fail" | "skipped" {
  if (rootCauseCode === "PASS") return "pass";

  const codeToStep: Record<string, number> = {
    INPUT_INVALID: 1,
    NO_CONTEXT_PROVIDED: 1,
    NO_RESPONSE_GENERATED: 1,
    SHOULD_HAVE_REFUSED: 2,
    FALSE_REFUSAL: 2,
    RETRIEVAL_MISS: 3,
    NO_RELEVANT_DOCS_RETRIEVED: 3,
    EXCESSIVE_NOISE: 3,
    HALLUCINATION: 4,
    EVIDENCE_NOT_USED: 4,
    GENERATION_UNFAITHFUL: 5,
    OFF_TOPIC_RESPONSE: 5,
    CHUNK_BOUNDARY_BROKEN: 4,
    CHUNK_INCOHERENT: 4,
    CHUNK_TOO_SPARSE: 4,
    CHUNK_TOO_DENSE: 4,
  };

  const failStep = codeToStep[rootCauseCode] || 6;

  if (stepId < failStep) return "pass";
  if (stepId === failStep) return "fail";
  return "skipped";
}

export function CascadeViz({ rootCauseCode, attribution }: CascadeVizProps) {
  return (
    <div className="space-y-1">
      {CASCADE_STEPS.map((step, i) => {
        const status = getStepStatus(step.id, rootCauseCode);
        return (
          <div key={step.id} className="flex items-center gap-3">
            <div
              className={cn(
                "w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0",
                status === "pass" && "bg-emerald-500/20 text-emerald-400",
                status === "fail" && "bg-red-500/20 text-red-400",
                status === "skipped" && "bg-slate-700/50 text-slate-500",
              )}
            >
              {status === "pass" && <Check size={14} />}
              {status === "fail" && <X size={14} />}
              {status === "skipped" && <span className="text-xs">—</span>}
            </div>
            <div
              className={cn(
                "flex-1 py-2 px-3 rounded-md text-sm",
                status === "pass" && "text-slate-300",
                status === "fail" && "bg-red-500/10 text-red-300 border border-red-500/20",
                status === "skipped" && "text-slate-500",
              )}
            >
              <span className="font-medium">Step {step.id}:</span> {step.label}
              {status === "fail" && (
                <span className="ml-2 font-mono text-xs text-red-400">
                  {rootCauseCode}
                </span>
              )}
            </div>
            {i < CASCADE_STEPS.length - 1 && (
              <ChevronRight size={14} className="text-slate-600 flex-shrink-0" />
            )}
          </div>
        );
      })}
    </div>
  );
}

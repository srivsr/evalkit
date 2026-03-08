"use client";

import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Anomaly } from "@/lib/types";
import { SeverityPill } from "./SeverityPill";

interface AnomalyAlertsProps {
  anomalies: Anomaly[];
}

export function AnomalyAlerts({ anomalies }: AnomalyAlertsProps) {
  if (anomalies.length === 0) return null;

  return (
    <div className="space-y-3">
      {anomalies.map((anomaly, i) => (
        <div
          key={`${anomaly.code}-${i}`}
          className="flex items-start gap-3 rounded-lg border border-amber-500/20 bg-amber-500/5 p-4"
        >
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" />
          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex items-center gap-2">
              <code className="font-mono text-sm text-slate-200">{anomaly.code}</code>
              <SeverityPill severity={anomaly.severity} />
            </div>
            <p className="text-sm text-slate-300">{anomaly.message}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

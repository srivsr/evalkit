import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatScore(score: number | null): string {
  if (score === null || score === undefined) return "N/A";
  return score.toFixed(2);
}

export function formatPercent(value: number | null): string {
  if (value === null || value === undefined) return "N/A";
  return `${(value * 100).toFixed(1)}%`;
}

export function formatLatency(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function formatCost(usd: number): string {
  if (usd === 0) return "Free";
  if (usd < 0.01) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(2)}`;
}

export function timeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export function verdictColor(verdict: string): string {
  switch (verdict) {
    case "PASS": return "text-emerald-400";
    case "FAIL": return "text-red-400";
    case "WARN": return "text-amber-400";
    default: return "text-slate-400";
  }
}

export function verdictBg(verdict: string): string {
  switch (verdict) {
    case "PASS": return "bg-emerald-500/10 border-emerald-500/20";
    case "FAIL": return "bg-red-500/10 border-red-500/20";
    case "WARN": return "bg-amber-500/10 border-amber-500/20";
    default: return "bg-slate-500/10 border-slate-500/20";
  }
}

export function severityColor(severity: string): string {
  switch (severity) {
    case "blocker": return "bg-red-900 text-red-100";
    case "critical": return "bg-red-600 text-white";
    case "major": return "bg-amber-600 text-white";
    case "minor": return "bg-slate-600 text-slate-100";
    case "none": return "bg-emerald-600 text-white";
    default: return "bg-slate-500 text-white";
  }
}

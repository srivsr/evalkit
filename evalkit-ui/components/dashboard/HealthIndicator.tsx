"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function HealthIndicator() {
  const [status, setStatus] = useState<"ok" | "degraded" | "offline">("offline");
  const [version, setVersion] = useState<string>("");

  useEffect(() => {
    async function check() {
      try {
        const health = await api.health();
        setStatus(health.status === "ok" ? "ok" : "degraded");
        setVersion(health.version);
      } catch {
        setStatus("offline");
      }
    }
    check();
    const interval = setInterval(check, 30000);
    return () => clearInterval(interval);
  }, []);

  const colors = {
    ok: "bg-emerald-400",
    degraded: "bg-amber-400",
    offline: "bg-red-400",
  };

  return (
    <div className="flex items-center gap-2 text-xs text-slate-500">
      <span className={`w-2 h-2 rounded-full ${colors[status]}`} />
      <span>API {status}</span>
      {version && <span className="font-mono">v{version}</span>}
    </div>
  );
}

"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";
import { useApi } from "@/lib/hooks/useApi";
import { api } from "@/lib/api";
import type { EvaluationListItem } from "@/lib/types";
import { ProjectSelector } from "@/components/dashboard/ProjectSelector";
import { EvaluationTable } from "@/components/dashboard/EvaluationTable";
import { NewEvaluationDialog } from "@/components/eval/NewEvaluationDialog";

export default function DashboardPage() {
  const router = useRouter();
  const [projectId, setProjectId] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const { data: evaluations, loading, refetch } = useApi<EvaluationListItem[]>(
    () => (projectId ? api.evaluations.list(projectId) : Promise.resolve([])),
    [projectId],
  );

  function handleSuccess(runId: string) {
    setDialogOpen(false);
    refetch();
    router.push(`/dashboard/evaluation/${runId}`);
  }

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold">Evaluations</h1>
          <ProjectSelector selectedId={projectId} onSelect={setProjectId} />
        </div>
        {projectId && (
          <button
            onClick={() => setDialogOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-md text-sm font-medium transition-colors"
          >
            <Plus size={16} />
            New Evaluation
          </button>
        )}
      </div>

      {!projectId ? (
        <div className="text-center py-16 text-slate-500">
          <p className="text-lg mb-2">Select a project to view evaluations</p>
          <p className="text-sm">Use the dropdown above to pick or create a project.</p>
        </div>
      ) : loading ? (
        <div className="text-center py-16 text-slate-500">
          <div className="inline-block w-6 h-6 border-2 border-slate-600 border-t-emerald-400 rounded-full animate-spin" />
          <p className="mt-3 text-sm">Loading evaluations...</p>
        </div>
      ) : (
        <EvaluationTable evaluations={evaluations || []} />
      )}

      {projectId && (
        <NewEvaluationDialog
          projectId={projectId}
          open={dialogOpen}
          onClose={() => setDialogOpen(false)}
          onSuccess={handleSuccess}
        />
      )}
    </div>
  );
}

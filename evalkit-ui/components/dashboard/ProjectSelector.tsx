"use client";
import { useState } from "react";
import { ChevronDown, Plus } from "lucide-react";
import { useApi } from "@/lib/hooks/useApi";
import { api } from "@/lib/api";
import type { Project } from "@/lib/types";

interface ProjectSelectorProps {
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function ProjectSelector({ selectedId, onSelect }: ProjectSelectorProps) {
  const { data: projects, refetch } = useApi<Project[]>(() => api.projects.list());
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");

  const selected = projects?.find((p) => p.id === selectedId);

  async function handleCreate() {
    if (!newName.trim()) return;
    try {
      const project = await api.projects.create(newName.trim());
      refetch();
      onSelect(project.id);
      setNewName("");
      setCreating(false);
      setOpen(false);
    } catch {
      // ignore
    }
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-slate-800 border border-slate-700 text-sm hover:border-slate-600 transition-colors min-w-[180px]"
      >
        <span className="flex-1 text-left truncate">
          {selected?.name || "Select project..."}
        </span>
        <ChevronDown size={14} className="text-slate-400" />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1 w-64 bg-slate-900 border border-slate-700 rounded-md shadow-xl z-50">
          <div className="max-h-48 overflow-y-auto">
            {projects?.map((p) => (
              <button
                key={p.id}
                onClick={() => {
                  onSelect(p.id);
                  setOpen(false);
                }}
                className="w-full text-left px-3 py-2 text-sm hover:bg-slate-800 transition-colors truncate"
              >
                {p.name}
              </button>
            ))}
            {(!projects || projects.length === 0) && (
              <div className="px-3 py-2 text-sm text-slate-500">No projects yet</div>
            )}
          </div>
          <div className="border-t border-slate-700 p-2">
            {creating ? (
              <div className="flex gap-2">
                <input
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                  className="flex-1 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
                  placeholder="Project name"
                  autoFocus
                />
                <button
                  onClick={handleCreate}
                  className="px-2 py-1 bg-emerald-600 rounded text-xs font-medium hover:bg-emerald-500 transition-colors"
                >
                  Add
                </button>
              </div>
            ) : (
              <button
                onClick={() => setCreating(true)}
                className="flex items-center gap-2 w-full px-2 py-1 text-sm text-emerald-400 hover:text-emerald-300 transition-colors"
              >
                <Plus size={14} /> New Project
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

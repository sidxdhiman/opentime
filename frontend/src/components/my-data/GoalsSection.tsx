"use client";

import { useState } from "react";
import { Check, Pencil, Plus, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ImpactWarningBanner } from "./ImpactWarningBanner";
import { SectionCard } from "./SectionCard";
import { type Goal, myDataApi } from "@/lib/myDataApi";

const CATEGORIES = [
  "career","education","health","relationships",
  "finance","creativity","personal_growth","lifestyle","other",
];

const STATUS_LABELS: Record<string, string> = {
  active: "Active", completed: "Completed", paused: "Paused", abandoned: "Removed",
};
const STATUS_COLORS: Record<string, string> = {
  active: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10",
  completed: "text-violet-400 border-violet-500/30 bg-violet-500/10",
  paused: "text-amber-400 border-amber-500/30 bg-amber-500/10",
  abandoned: "text-muted border-border bg-secondary/30",
};

interface EditState {
  title: string;
  description: string;
  category: string;
  importance: number;
  status: string;
}

function GoalRow({ goal, onUpdated, onDeleted }: {
  goal: Goal;
  onUpdated: (g: Goal) => void;
  onDeleted: (id: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [showWarning, setShowWarning] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<EditState>({
    title: goal.title,
    description: goal.description ?? "",
    category: goal.category,
    importance: goal.importance,
    status: goal.status,
  });

  const startEdit = () => { setShowWarning(true); setEditing(true); setError(null); };
  const cancelEdit = () => { setEditing(false); setShowWarning(false); setDraft({ title: goal.title, description: goal.description ?? "", category: goal.category, importance: goal.importance, status: goal.status }); };

  const save = async () => {
    setSaving(true); setError(null);
    try {
      const updated = await myDataApi.updateGoal(goal.id, { ...draft, description: draft.description || null });
      onUpdated(updated);
      setEditing(false); setShowWarning(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Save failed.");
    } finally { setSaving(false); }
  };

  const remove = async () => {
    if (!confirm("Remove this goal? It will be marked as abandoned but not deleted.")) return;
    setSaving(true);
    try {
      await myDataApi.deleteGoal(goal.id);
      onDeleted(goal.id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Delete failed.");
      setSaving(false);
    }
  };

  if (goal.status === "abandoned") return null;

  return (
    <div className="rounded-xl border border-border bg-secondary/20 p-4 space-y-3">
      {showWarning && <ImpactWarningBanner onDismiss={() => setShowWarning(false)} />}

      {editing ? (
        <div className="space-y-3">
          <Input value={draft.title} onChange={(e) => setDraft((d) => ({ ...d, title: e.target.value }))} placeholder="Goal title" autoFocus />
          <textarea className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm resize-y focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" rows={2} placeholder="Description (optional)" value={draft.description} onChange={(e) => setDraft((d) => ({ ...d, description: e.target.value }))} />
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-muted mb-1 block">Category</label>
              <select value={draft.category} onChange={(e) => setDraft((d) => ({ ...d, category: e.target.value }))} className="flex h-9 w-full rounded-lg border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                {CATEGORIES.map((c) => <option key={c} value={c}>{c.replace("_", " ")}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-muted mb-1 block">Status</label>
              <select value={draft.status} onChange={(e) => setDraft((d) => ({ ...d, status: e.target.value }))} className="flex h-9 w-full rounded-lg border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                {["active","completed","paused"].map((s) => <option key={s} value={s}>{STATUS_LABELS[s]}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="text-xs text-muted mb-1 block">Importance: {Math.round(draft.importance * 100)}%</label>
            <input type="range" min={0} max={1} step={0.05} value={draft.importance} onChange={(e) => setDraft((d) => ({ ...d, importance: parseFloat(e.target.value) }))} className="w-full accent-violet-500" />
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
          <div className="flex gap-2 justify-end">
            <Button type="button" variant="ghost" size="sm" onClick={cancelEdit} disabled={saving}><X className="h-3.5 w-3.5 mr-1" />Cancel</Button>
            <Button type="button" size="sm" onClick={save} disabled={saving || !draft.title.trim()} className="bg-violet-600 hover:bg-violet-500 text-white"><Check className="h-3.5 w-3.5 mr-1" />{saving ? "Saving..." : "Save"}</Button>
          </div>
        </div>
      ) : (
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-medium text-sm text-foreground">{goal.title}</span>
              <span className={`text-xs border rounded-full px-2 py-0.5 ${STATUS_COLORS[goal.status] ?? ""}`}>{STATUS_LABELS[goal.status] ?? goal.status}</span>
              <span className="text-xs text-muted border border-border rounded-full px-2 py-0.5">{goal.category.replace("_", " ")}</span>
            </div>
            {goal.description && <p className="text-xs text-muted mt-1 line-clamp-2">{goal.description}</p>}
            <div className="mt-2 flex items-center gap-2">
              <div className="h-1 flex-1 max-w-[120px] rounded-full bg-border overflow-hidden"><div className="h-full bg-violet-500 transition-all" style={{ width: `${goal.importance * 100}%` }} /></div>
              <span className="text-xs text-muted">{Math.round(goal.importance * 100)}% importance</span>
            </div>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <button type="button" onClick={startEdit} className="p-1.5 rounded-lg text-muted hover:text-foreground hover:bg-secondary transition-colors" aria-label="Edit goal"><Pencil className="h-3.5 w-3.5" /></button>
            <button type="button" onClick={remove} disabled={saving} className="p-1.5 rounded-lg text-muted hover:text-destructive hover:bg-destructive/10 transition-colors" aria-label="Remove goal"><Trash2 className="h-3.5 w-3.5" /></button>
          </div>
        </div>
      )}
    </div>
  );
}

export function GoalsSection({ initialGoals }: { initialGoals: Goal[] }) {
  const [goals, setGoals] = useState(initialGoals);
  const [adding, setAdding] = useState(false);
  const [showAddWarning, setShowAddWarning] = useState(false);
  const [newGoal, setNewGoal] = useState({ title: "", description: "", category: "other", importance: 0.75 });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const saveNew = async () => {
    if (!newGoal.title.trim()) return;
    setSaving(true); setError(null);
    try {
      const created = await myDataApi.createGoal({ ...newGoal, description: newGoal.description || null });
      setGoals((g) => [...g, created]);
      setAdding(false); setShowAddWarning(false);
      setNewGoal({ title: "", description: "", category: "other", importance: 0.75 });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create goal.");
    } finally { setSaving(false); }
  };

  const visible = goals.filter((g) => g.status !== "abandoned");

  return (
    <SectionCard
      title="Goals"
      description="What you're working toward. Chronos uses these to track progress and surface relevant insights."
      action={
        <Button type="button" variant="outline" size="sm" onClick={() => { setAdding(true); setShowAddWarning(true); }} className="gap-1.5 border-violet-500/30 text-violet-400 hover:bg-violet-500/10 text-xs">
          <Plus className="h-3.5 w-3.5" />Add goal
        </Button>
      }
    >
      <div className="space-y-3">
        {visible.length === 0 && !adding && (
          <p className="text-sm text-muted text-center py-4">No active goals. Add one above.</p>
        )}

        {goals.map((g) => (
          <GoalRow key={g.id} goal={g}
            onUpdated={(updated) => setGoals((gs) => gs.map((x) => x.id === updated.id ? updated : x))}
            onDeleted={(id) => setGoals((gs) => gs.map((x) => x.id === id ? { ...x, status: "abandoned" as const } : x))}
          />
        ))}

        {adding && (
          <div className="rounded-xl border border-violet-500/30 bg-violet-500/5 p-4 space-y-3">
            {showAddWarning && <ImpactWarningBanner onDismiss={() => setShowAddWarning(false)} />}
            <Input value={newGoal.title} onChange={(e) => setNewGoal((d) => ({ ...d, title: e.target.value }))} placeholder="New goal title..." autoFocus />
            <textarea className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm resize-y focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" rows={2} placeholder="Description (optional)" value={newGoal.description} onChange={(e) => setNewGoal((d) => ({ ...d, description: e.target.value }))} />
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-muted mb-1 block">Category</label>
                <select value={newGoal.category} onChange={(e) => setNewGoal((d) => ({ ...d, category: e.target.value }))} className="flex h-9 w-full rounded-lg border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  {CATEGORIES.map((c) => <option key={c} value={c}>{c.replace("_", " ")}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-muted mb-1 block">Importance: {Math.round(newGoal.importance * 100)}%</label>
                <input type="range" min={0} max={1} step={0.05} value={newGoal.importance} onChange={(e) => setNewGoal((d) => ({ ...d, importance: parseFloat(e.target.value) }))} className="w-full mt-2 accent-violet-500" />
              </div>
            </div>
            {error && <p className="text-xs text-destructive">{error}</p>}
            <div className="flex gap-2 justify-end">
              <Button type="button" variant="ghost" size="sm" onClick={() => { setAdding(false); setShowAddWarning(false); }}><X className="h-3.5 w-3.5 mr-1" />Cancel</Button>
              <Button type="button" size="sm" onClick={saveNew} disabled={saving || !newGoal.title.trim()} className="bg-violet-600 hover:bg-violet-500 text-white"><Check className="h-3.5 w-3.5 mr-1" />{saving ? "Saving..." : "Add goal"}</Button>
            </div>
          </div>
        )}
      </div>
    </SectionCard>
  );
}

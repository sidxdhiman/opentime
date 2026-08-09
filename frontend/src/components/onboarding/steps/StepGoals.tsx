"use client";

import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export interface GoalInput {
  title: string;
  description: string;
  category: string;
  importance: number;
}

interface Props {
  goals: GoalInput[];
  onChange: (goals: GoalInput[]) => void;
}

const CATEGORIES = [
  { value: "career", label: "Career" },
  { value: "education", label: "Education" },
  { value: "health", label: "Health" },
  { value: "relationships", label: "Relationships" },
  { value: "finance", label: "Finance" },
  { value: "creativity", label: "Creativity" },
  { value: "personal_growth", label: "Personal Growth" },
  { value: "lifestyle", label: "Lifestyle" },
  { value: "other", label: "Other" },
];

function GoalCard({ goal, index, onUpdate, onRemove }: {
  goal: GoalInput; index: number;
  onUpdate: (g: GoalInput) => void; onRemove: () => void;
}) {
  const set = (k: keyof GoalInput, v: string | number) => onUpdate({ ...goal, [k]: v });
  return (
    <div className="rounded-xl border border-border bg-secondary/30 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold text-muted uppercase tracking-wider">Goal {index + 1}</span>
        <button type="button" onClick={onRemove} className="text-muted hover:text-destructive transition-colors" aria-label="Remove goal">
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
      <div className="space-y-2">
        <Label className="text-xs">What do you want to achieve?</Label>
        <Input placeholder="Goal title..." value={goal.title} onChange={(e) => set("title", e.target.value)} autoFocus={index === 0} />
      </div>
      <div className="space-y-2">
        <Label className="text-xs">Description <span className="text-muted font-normal">(optional)</span></Label>
        <textarea className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm resize-y placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" placeholder="More detail..." rows={2} value={goal.description} onChange={(e) => set("description", e.target.value)} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-2">
          <Label className="text-xs">Category</Label>
          <select value={goal.category} onChange={(e) => set("category", e.target.value)} className="flex h-10 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
            {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </div>
        <div className="space-y-2">
          <Label className="text-xs">Importance</Label>
          <input type="range" min={0} max={1} step={0.25} value={goal.importance} onChange={(e) => set("importance", parseFloat(e.target.value))} className="w-full mt-2 accent-violet-500" />
        </div>
      </div>
    </div>
  );
}

export function StepGoals({ goals, onChange }: Props) {
  const addGoal = () => onChange([...goals, { title: "", description: "", category: "other", importance: 0.75 }]);
  return (
    <div className="space-y-4">
      {goals.length === 0 && (
        <p className="text-sm text-muted italic text-center py-4">No goals yet. Add at least one thing you&apos;re working toward.</p>
      )}
      {goals.map((g, i) => (
        <GoalCard key={i} goal={g} index={i} onUpdate={(u) => { const next = [...goals]; next[i] = u; onChange(next); }} onRemove={() => onChange(goals.filter((_, idx) => idx !== i))} />
      ))}
      <Button type="button" variant="outline" onClick={addGoal} className="w-full border-dashed border-violet-500/40 text-violet-400 hover:bg-violet-500/10">
        <Plus className="h-4 w-4 mr-2" />Add a goal
      </Button>
    </div>
  );
}

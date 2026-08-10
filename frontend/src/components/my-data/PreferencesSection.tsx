"use client";

import { useState } from "react";
import { Check, Pencil, Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ImpactWarningBanner } from "./ImpactWarningBanner";
import { SectionCard } from "./SectionCard";
import { type AnalysisPref, myDataApi } from "@/lib/myDataApi";

const PRESET_OPTIONS = [
  { value: "how_i_changed", label: "How I've changed" },
  { value: "habits_patterns", label: "Habits and patterns" },
  { value: "goals_progress", label: "Goals and progress" },
  { value: "thoughts_beliefs", label: "Thoughts and beliefs" },
  { value: "relationships", label: "Relationships" },
  { value: "career", label: "Career" },
  { value: "emotional_patterns", label: "Emotional patterns" },
  { value: "things_i_forget", label: "Things I tend to forget" },
];

function prefLabel(value: string) {
  return PRESET_OPTIONS.find((o) => o.value === value)?.label ?? value;
}

export function PreferencesSection({ initialPrefs }: { initialPrefs: AnalysisPref[] }) {
  const [prefs, setPrefs] = useState(initialPrefs.map((p) => p.preference));
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<string[]>([]);
  const [custom, setCustom] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startEdit = () => {
    setDraft([...prefs]);
    setEditing(true);
    setError(null);
  };

  const cancelEdit = () => { setEditing(false); setCustom(""); };

  const toggle = (val: string) => {
    setDraft((d) => d.includes(val) ? d.filter((x) => x !== val) : [...d, val]);
  };

  const addCustom = () => {
    const t = custom.trim();
    if (!t || draft.includes(t)) return;
    setDraft((d) => [...d, t]);
    setCustom("");
  };

  const save = async () => {
    setSaving(true); setError(null);
    try {
      await myDataApi.updatePreferences(draft);
      setPrefs(draft);
      setEditing(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Save failed.");
    } finally { setSaving(false); }
  };

  return (
    <SectionCard
      title="Analysis Preferences"
      description="What Chronos focuses on when building insights about you."
      action={!editing ? (
        <Button type="button" variant="outline" size="sm" onClick={startEdit} className="gap-1.5 border-violet-500/30 text-violet-400 hover:bg-violet-500/10 text-xs">
          <Pencil className="h-3.5 w-3.5" />Edit
        </Button>
      ) : undefined}
    >
      {editing ? (
        <div className="space-y-4">
          <ImpactWarningBanner />
          <div className="grid grid-cols-2 gap-2">
            {PRESET_OPTIONS.map((opt) => {
              const on = draft.includes(opt.value);
              return (
                <button key={opt.value} type="button" onClick={() => toggle(opt.value)}
                  className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-xs text-left transition-all ${on ? "border-violet-500/60 bg-violet-500/10 text-violet-300" : "border-border bg-secondary/20 text-foreground hover:border-violet-500/30"}`}
                >
                  <span className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-all ${on ? "border-violet-500 bg-violet-500" : "border-border"}`}>
                    {on && <Check className="h-2.5 w-2.5 text-white" />}
                  </span>
                  {opt.label}
                </button>
              );
            })}
          </div>
          {/* custom tags */}
          {draft.filter((d) => !PRESET_OPTIONS.some((o) => o.value === d)).length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {draft.filter((d) => !PRESET_OPTIONS.some((o) => o.value === d)).map((d) => (
                <span key={d} className="flex items-center gap-1 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-2.5 py-0.5 text-xs text-indigo-300">
                  {d}
                  <button type="button" onClick={() => setDraft((prev) => prev.filter((x) => x !== d))} className="hover:text-destructive">×</button>
                </span>
              ))}
            </div>
          )}
          <div className="flex gap-2">
            <Input placeholder="Add a custom preference..." value={custom} onChange={(e) => setCustom(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addCustom(); }}} className="text-sm" />
            <Button type="button" variant="outline" onClick={addCustom} className="shrink-0 border-violet-500/40 text-violet-400 hover:bg-violet-500/10"><Plus className="h-4 w-4" /></Button>
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
          <div className="flex gap-2 justify-end">
            <Button type="button" variant="ghost" size="sm" onClick={cancelEdit}><X className="h-3.5 w-3.5 mr-1" />Cancel</Button>
            <Button type="button" size="sm" onClick={save} disabled={saving} className="bg-violet-600 hover:bg-violet-500 text-white"><Check className="h-3.5 w-3.5 mr-1" />{saving ? "Saving..." : "Save"}</Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {prefs.length === 0 && <p className="text-sm text-muted">No preferences set.</p>}
          {prefs.map((p) => (
            <span key={p} className="rounded-full border border-violet-500/30 bg-violet-500/8 px-3 py-1 text-xs text-violet-300">
              {prefLabel(p)}
            </span>
          ))}
        </div>
      )}
    </SectionCard>
  );
}

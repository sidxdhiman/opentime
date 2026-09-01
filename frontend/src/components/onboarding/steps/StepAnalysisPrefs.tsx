"use client";

import { useState } from "react";
import { Check, Plus } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const PRESET_OPTIONS = [
  { value: "how_i_changed", label: "How I've changed" },
  { value: "habits_patterns", label: "My habits and patterns" },
  { value: "goals_progress", label: "My goals and progress" },
  { value: "thoughts_beliefs", label: "My thoughts and beliefs" },
  { value: "relationships", label: "My relationships" },
  { value: "career", label: "My career" },
  { value: "emotional_patterns", label: "My emotional patterns" },
  { value: "things_i_forget", label: "Things I tend to forget" },
];

interface Props {
  selected: string[];
  onChange: (selected: string[]) => void;
}

export function StepAnalysisPrefs({ selected, onChange }: Props) {
  const [customText, setCustomText] = useState("");

  const toggle = (value: string) => {
    onChange(
      selected.includes(value)
        ? selected.filter((s) => s !== value)
        : [...selected, value]
    );
  };

  const addCustom = () => {
    const trimmed = customText.trim();
    if (!trimmed || selected.includes(trimmed)) return;
    onChange([...selected, trimmed]);
    setCustomText("");
  };

  const removeCustom = (value: string) => {
    onChange(selected.filter((s) => s !== value));
  };

  const customSelected = selected.filter(
    (s) => !PRESET_OPTIONS.some((o) => o.value === s)
  );

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3">
        {PRESET_OPTIONS.map((opt) => {
          const isSelected = selected.includes(opt.value);
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => toggle(opt.value)}
              aria-pressed={isSelected}
              className={`flex items-center gap-2 rounded-xl border px-4 py-3 text-sm text-left transition-all ${
                isSelected
                  ? "border-violet-500/60 bg-violet-500/10 text-violet-300"
                  : "border-border bg-secondary/20 text-foreground hover:border-violet-500/30 hover:bg-violet-500/5"
              }`}
            >
              <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition-all ${isSelected ? "border-violet-500 bg-violet-500" : "border-border"}`}>
                {isSelected && <Check className="h-3 w-3 text-white" />}
              </span>
              {opt.label}
            </button>
          );
        })}
      </div>

      {/* Custom entries */}
      {customSelected.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {customSelected.map((s) => (
            <span key={s} className="flex items-center gap-1 rounded-full border border-indigo-500/40 bg-indigo-500/10 px-3 py-1 text-xs text-indigo-300">
              {s}
              <button type="button" onClick={() => removeCustom(s)} className="ml-1 hover:text-destructive" aria-label={`Remove ${s}`}>×</button>
            </span>
          ))}
        </div>
      )}

      {/* Add custom */}
      <div className="flex gap-2">
        <Input
          aria-label="A custom area to track"
          placeholder="Something else you want Chronos to track..."
          value={customText}
          onChange={(e) => setCustomText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addCustom(); } }}
        />
        <Button type="button" variant="outline" onClick={addCustom} aria-label="Add custom area to track" className="shrink-0 border-violet-500/40 text-violet-400 hover:bg-violet-500/10">
          <Plus className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

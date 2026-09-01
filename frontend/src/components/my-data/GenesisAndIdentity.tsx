"use client";

import { useState } from "react";
import { Check, Pencil, Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ImpactWarningBanner } from "./ImpactWarningBanner";
import { SectionCard } from "./SectionCard";
import { type GenesisMemory, type IdentityState, myDataApi } from "@/lib/myDataApi";

// ── Genesis Memory ───────────────────────────────────────────────────────────

export function GenesisSection({ initialMemory }: { initialMemory: GenesisMemory | null }) {
  const [memory, setMemory] = useState(initialMemory);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(initialMemory?.content ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startEdit = () => { setDraft(memory?.content ?? ""); setEditing(true); setError(null); };
  const cancel = () => { setEditing(false); setError(null); };

  const save = async () => {
    if (draft.trim().length < 10) { setError("Must be at least 10 characters."); return; }
    setSaving(true); setError(null);
    try {
      const updated = await myDataApi.updateGenesis(draft.trim());
      setMemory(updated as unknown as GenesisMemory);
      setEditing(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Save failed.");
    } finally { setSaving(false); }
  };

  return (
    <SectionCard
      title="Genesis Memory"
      description="The first thing Chronos remembers about you. This anchors your entire personal history."
      action={!editing && memory ? (
        <Button type="button" variant="outline" size="sm" onClick={startEdit} className="gap-1.5 border-accent/60 text-accent-foreground hover:bg-accent text-xs">
          <Pencil className="h-3.5 w-3.5" />Edit
        </Button>
      ) : undefined}
    >
      {!memory ? (
        <p className="text-sm text-muted">No genesis memory found. Complete onboarding to create one.</p>
      ) : editing ? (
        <div className="space-y-3">
          <ImpactWarningBanner />
          <textarea
            aria-label="Genesis memory content"
            className="w-full rounded-lg border border-input bg-background px-4 py-3 text-sm leading-relaxed resize-y focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            rows={8}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            autoFocus
          />
          {error && <p role="alert" className="text-xs text-destructive">{error}</p>}
          <div className="flex gap-2 justify-end">
            <Button type="button" variant="ghost" size="sm" onClick={cancel}><X className="h-3.5 w-3.5 mr-1" />Cancel</Button>
            <Button type="button" size="sm" onClick={save} disabled={saving} className="bg-primary text-primary-foreground hover:bg-primary/90"><Check className="h-3.5 w-3.5 mr-1" />{saving ? "Saving..." : "Save"}</Button>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-foreground/80 leading-relaxed whitespace-pre-wrap">{memory.content}</p>
          <div className="flex flex-wrap gap-2">
            {memory.topics?.map((t) => (
              <span key={t} className="rounded-full border border-border bg-secondary/30 px-2.5 py-0.5 text-xs text-muted">{t}</span>
            ))}
          </div>
          <p className="text-xs text-muted/60">
            Written {new Date(memory.created_at).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" })}
          </p>
        </div>
      )}
    </SectionCard>
  );
}

// ── Identity Traits ──────────────────────────────────────────────────────────

export function IdentitySection({ initialIdentity }: { initialIdentity: IdentityState | null }) {
  const [identity, setIdentity] = useState(initialIdentity);
  const [editing, setEditing] = useState(false);
  const [draftTraits, setDraftTraits] = useState<string[]>([]);
  const [newTrait, setNewTrait] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startEdit = () => {
    setDraftTraits(identity?.traits.map((t) => t.trait) ?? []);
    setEditing(true); setError(null);
  };
  const cancel = () => { setEditing(false); setNewTrait(""); };

  const addTrait = () => {
    const t = newTrait.trim();
    if (!t || draftTraits.includes(t)) return;
    setDraftTraits((d) => [...d, t]);
    setNewTrait("");
  };

  const removeTrait = (t: string) => setDraftTraits((d) => d.filter((x) => x !== t));

  const save = async () => {
    setSaving(true); setError(null);
    try {
      const updated = await myDataApi.updateTraits(draftTraits);
      setIdentity(updated);
      setEditing(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Save failed.");
    } finally { setSaving(false); }
  };

  const interests = identity?.interests?.map((c) => c.value).filter(Boolean) ?? [];
  const values = identity?.values?.map((c) => c.value).filter(Boolean) ?? [];

  return (
    <SectionCard
      title="Identity Snapshot"
      description={`Version ${identity?.version ?? 1} — how Chronos currently understands you. Editing creates a new version; history is preserved.`}
      action={!editing && identity ? (
        <Button type="button" variant="outline" size="sm" onClick={startEdit} className="gap-1.5 border-accent/60 text-accent-foreground hover:bg-accent text-xs">
          <Pencil className="h-3.5 w-3.5" />Edit traits
        </Button>
      ) : undefined}
    >
      {!identity ? (
        <p className="text-sm text-muted">No identity data yet.</p>
      ) : (
        <div className="space-y-5">
          {/* Traits */}
          <div>
            <p className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">Traits</p>
            {editing ? (
              <div className="space-y-3">
                <ImpactWarningBanner />
                <div className="flex flex-wrap gap-2">
                  {draftTraits.map((t) => (
                    <span key={t} className="flex items-center gap-1 rounded-full border border-accent/50 bg-accent px-3 py-1 text-xs text-accent-foreground">
                      {t}
                      <button type="button" onClick={() => removeTrait(t)} className="hover:text-destructive" aria-label={`Remove ${t}`}>×</button>
                    </span>
                  ))}
                  {draftTraits.length === 0 && <p className="text-xs text-muted">No traits yet.</p>}
                </div>
                <div className="flex gap-2">
                  <Input aria-label="New trait" placeholder="Add a trait..." value={newTrait} onChange={(e) => setNewTrait(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addTrait(); }}} className="text-sm" />
                  <Button type="button" variant="outline" onClick={addTrait} aria-label="Add trait" className="shrink-0 border-accent/60 text-accent-foreground hover:bg-accent"><Plus className="h-4 w-4" /></Button>
                </div>
{error && <p role="alert" className="text-xs text-destructive">{error}</p>}
                <div className="flex gap-2 justify-end">
                  <Button type="button" variant="ghost" size="sm" onClick={cancel}><X className="h-3.5 w-3.5 mr-1" />Cancel</Button>
                  <Button type="button" size="sm" onClick={save} disabled={saving} className="bg-primary text-primary-foreground hover:bg-primary/90"><Check className="h-3.5 w-3.5 mr-1" />{saving ? "Saving..." : "Save"}</Button>
                </div>
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {identity.traits.length === 0 && <p className="text-xs text-muted">None detected yet.</p>}
                {identity.traits.map((t) => (
                  <span key={t.trait} className="rounded-full border border-border bg-secondary/30 px-3 py-1 text-xs text-foreground/80">
                    {t.trait}
                    <span className="ml-1.5 text-muted text-[10px]">{Math.round(t.confidence * 100)}%</span>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Interests (read-only — LLM inferred) */}
          {interests.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">Interests <span className="font-normal normal-case text-muted/50">(inferred by Chronos)</span></p>
              <div className="flex flex-wrap gap-2">
                {interests.map((v: string) => (
                  <span key={v} className="rounded-full border border-border bg-secondary/40 px-3 py-1 text-xs text-foreground/80">{v}</span>
                ))}
              </div>
            </div>
          )}

          {/* Values */}
          {values.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">Values <span className="font-normal normal-case text-muted/50">(inferred by Chronos)</span></p>
              <div className="flex flex-wrap gap-2">
                {values.map((v: string) => (
                  <span key={v} className="rounded-full border border-border bg-secondary/40 px-3 py-1 text-xs text-foreground/80">{v}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </SectionCard>
  );
}

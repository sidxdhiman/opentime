"use client";

import { useState, useEffect, useRef } from "react";
import { CheckCircle2, Download, Loader2, ShieldAlert, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { chronosApi } from "@/lib/chronosApi";
import { errorMessage } from "@/lib/http";

export function DataControls() {
  const [exporting, setExporting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const deleteTriggerRef = useRef<HTMLButtonElement | null>(null);
  const confirmDeleteRef = useRef<HTMLButtonElement | null>(null);
  const wasConfirmingRef = useRef(false);

  useEffect(() => {
    if (confirmingDelete === wasConfirmingRef.current) return;
    wasConfirmingRef.current = confirmingDelete;
    if (confirmingDelete) {
      confirmDeleteRef.current?.focus();
    } else {
      deleteTriggerRef.current?.focus();
    }
  }, [confirmingDelete]);

  async function handleExport() {
    setExporting(true);
    setMessage(null);
    try {
      const data = await chronosApi.exportData();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `opentime-data-export-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      // Defer revocation so the browser can finish initiating the download.
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setMessage({
        type: "success",
        text: "Your ChronOS data has been exported as a JSON file.",
      });
    } catch (e: unknown) {
      setMessage({
        type: "error",
        text: errorMessage(e),
      });
    } finally {
      setExporting(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    setMessage(null);
    try {
      await chronosApi.deleteAllData();
      setMessage({
        type: "success",
        text: "All ChronOS data associated with your account has been permanently deleted.",
      });
      setConfirmingDelete(false);
    } catch (e: unknown) {
      setMessage({
        type: "error",
        text: errorMessage(e),
      });
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="rounded-2xl border border-border bg-card shadow-card">
      <div className="flex items-start justify-between border-b border-border/60 px-6 py-4">
        <div>
          <h2 className="font-semibold text-foreground">Your data, your control</h2>
          <p className="text-xs text-muted mt-0.5">
            Download everything Chronos remembers about you, or permanently remove it from your account.
          </p>
        </div>
      </div>
      <div className="px-6 py-5 space-y-4">
        {message && (
          <div
            role={message.type === "error" ? "alert" : "status"}
            className={`flex items-start gap-2 rounded-lg border px-3 py-2.5 text-sm ${
              message.type === "success"
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                : "border-destructive/30 bg-destructive/10 text-destructive"
            }`}
          >
            {message.type === "success" ? (
              <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" />
            ) : (
              <ShieldAlert className="h-4 w-4 mt-0.5 shrink-0" />
            )}
            {message.text}
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-3">
          <Button variant="outline" onClick={handleExport} disabled={exporting || deleting} className="flex-1">
            {exporting ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" /> : <Download className="h-4 w-4" />}
            Export all my data
          </Button>

          {!confirmingDelete ? (
            <Button
              ref={deleteTriggerRef}
              variant="destructive"
              onClick={() => setConfirmingDelete(true)}
              disabled={exporting || deleting}
              className="flex-1"
            >
              <Trash2 className="h-4 w-4" />
              Delete all my ChronOS data
            </Button>
          ) : (
            <div className="flex flex-1 flex-col gap-1">
              <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                This permanently deletes all ChronOS memories, timeline, identity, reflections, patterns and stories.
                This cannot be undone.
              </div>
              <div className="flex gap-2">
                <Button
                  ref={confirmDeleteRef}
                  variant="destructive"
                  onClick={handleDelete}
                  disabled={deleting}
                  className="flex-1"
                >
                  {deleting ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" /> : <Trash2 className="h-4 w-4" />}
                  Yes, delete everything
                </Button>
                <Button variant="ghost" onClick={() => setConfirmingDelete(false)} disabled={deleting} className="flex-1">
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

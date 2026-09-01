#!/usr/bin/env node
/**
 * Static regression guard for Phase 5E-E (and 5E-D): ensures the frontend
 * never renders engine internals in user-facing surfaces.
 *
 * Layers:
 *   1. DISPLAY IDENTIFIERS — fields that must never be read for display
 *      (provider_name, model_name, reasoning_steps, confidence_score, ...).
 *      Scanned across the UI layers (src/components/** + src/app/**), where
 *      any occurrence is a leak. Type plumbing files and the recorder's
 *      form-encoding path are excluded: internal field names legitimately
 *      live in API types and request payloads.
 *   2. ID LITERALS — the backend's internal identifier conventions
 *      (mem_, tevent_, thread_, resp_, evidence_, state_). These prefixes
 *      must never appear inside user-facing text. Comment-stripped scan
 *      across ALL of src; identifiers such as "suggested_thread_id" or
 *      "past_state_summary" (no digit run) are intentionally not matched.
 *   3. INTERNAL WORDS — "mongo" / "embedding" / "system prompt" inside UI
 *      layer files.
 *
 * Exit code is non-zero on any finding. Run with `npm run check:leakage`.
 */

import { readdir, readFile } from "node:fs/promises";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const SRC = join(ROOT, "src");
const UI_DIRS = [join(SRC, "components"), join(SRC, "app")];

/** Display-surface files that legitimately reference internal field names:
 *  API/type plumbing, the deterministic explanation translator, and the
 *  recorder's request-encoding path. */
const SKIP_IDENTIFIER_SCAN = new Set([
  join(SRC, "lib/chronosApi.ts"),
  join(SRC, "lib/explainability.ts"),
  join(SRC, "lib/myDataApi.ts"),
  join(SRC, "components/chronos/VoiceVideoRecorder.tsx"),
]);

/** Field identifiers that are engine internals — never user-facing. */
const FORBIDDEN_IDENTIFIERS = [
  "provider_name",
  "model_name",
  "processing_time_ms",
  "prompt_context",
  "system_prompt",
  "user_prompt",
  "raw_llm_response",
  "reasoning_steps",
  "reasoning_trace",
  "context_sources",
  "ai_execution_steps",
  "ai_execution",
  "inference_policy",
  "confidence_score",
  "personalization_score",
  "validation_result",
  "ai_routing",
];

/**
 * Internal identifier conventions, e.g. "mem_", "tevent_", "thread_".
 * A prefix is only reported as a leak when followed by an id-like run —
 * one that contains a digit or is 8+ chars long — so type fields such as
 * "evidence_count", "past_state_summary" and "suggested_thread_id" are
 * never false positives.
 */
const ID_LITERAL_PATTERN = /\b(?:mem|tevent|thread|resp|evidence|state)_([a-z0-9_-]+)/g;

/** Words that only ever describe internal machinery. */
const FORBIDDEN_WORDS = ["mongo", "embedding", "system prompt"];

function stripComments(source) {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/\/\/[^\n]*/g, "");
}

async function listFiles(dir) {
  const out = [];
  const entries = await readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...(await listFiles(full)));
    } else if (/\.(ts|tsx)$/.test(entry.name)) {
      out.push(full);
    }
  }
  return out;
}

async function main() {
  const findings = [];
  const allSource = await listFiles(SRC);

  // --- Layer 1: display identifiers (UI layers only) ----------------------
  for (const dir of UI_DIRS) {
    const files = await listFiles(dir);
    for (const file of files) {
      if (SKIP_IDENTIFIER_SCAN.has(file)) continue;
      const content = await readFile(file, "utf8");
      const rel = relative(ROOT, file);
      for (const ident of FORBIDDEN_IDENTIFIERS) {
        if (content.includes(ident)) {
          findings.push(`${rel}: reads internal field "${ident}" for display`);
        }
      }
      // supporting_memory_ids is allowed only for counting grounded moments
      // ("based on N things you've shared"); it may never be rendered raw.
      for (const m of content.matchAll(/supporting_memory_ids(?!\s*\??\s*\.\s*length\b)/g)) {
        const line = content.slice(0, m.index).split("\n").length;
        findings.push(`${rel}:${line}: supporting_memory_ids used outside a length check`);
      }
    }
  }

  // --- Layer 2: internal id literals (all layers, comment-free) -----------
  for (const file of allSource) {
    const content = stripComments(await readFile(file, "utf8"));
    const rel = relative(ROOT, file);
    for (const m of content.matchAll(ID_LITERAL_PATTERN)) {
      const run = m[1];
      if (!(/[0-9]/.test(run) || run.length >= 8)) continue;
      const line = content.slice(0, m.index).split("\n").length;
      findings.push(`${rel}:${line}: internal id literal "${m[0]}"`);
    }
  }

  // --- Layer 3: internal words inside UI layer string/JSX text ------------
  for (const dir of UI_DIRS) {
    const files = await listFiles(dir);
    for (const file of files) {
      if (SKIP_IDENTIFIER_SCAN.has(file)) continue;
      const content = stripComments(await readFile(file, "utf8"));
      const rel = relative(ROOT, file);
      for (const word of FORBIDDEN_WORDS) {
        const idx = content.indexOf(word);
        if (idx !== -1) {
          const line = content.slice(0, idx).split("\n").length;
          findings.push(`${rel}:${line}: internal word "${word}"`);
        }
      }
    }
  }

  if (findings.length > 0) {
    console.error("Explainability leak check FAILED:");
    for (const f of findings) console.error(`  [x] ${f}`);
    process.exit(1);
  }

  console.log(`Explainability leak check passed (${allSource.length} files).`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
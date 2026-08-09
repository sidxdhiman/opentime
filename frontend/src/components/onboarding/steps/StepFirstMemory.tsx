"use client";

interface Props {
  value: string;
  onChange: (v: string) => void;
}

export function StepFirstMemory({ value, onChange }: Props) {
  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-violet-500/20 bg-violet-500/5 p-4 text-sm text-violet-300 leading-relaxed">
        <p className="font-semibold mb-1">This becomes your Genesis Memory.</p>
        <p className="text-violet-300/70">
          It&apos;s the first thing Chronos will remember about you. Write freely —
          your thoughts, where you are in life, how you feel, what matters to
          you today. Your future self will look back at this.
        </p>
      </div>

      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Write something you want your future self to remember about who you are today..."
        rows={10}
        autoFocus
        className="w-full rounded-lg border border-input bg-background px-4 py-3 text-sm leading-relaxed resize-y placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500"
      />

      <p className="text-xs text-muted">
        Audio and video memory support coming soon. For now, write as much or as
        little as you want.
      </p>
    </div>
  );
}

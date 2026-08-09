"use client";

interface Props {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  minRows?: number;
}

export function StepFreeText({ value, onChange, placeholder, minRows = 8 }: Props) {
  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      rows={minRows}
      autoFocus
      className="w-full rounded-lg border border-input bg-background px-4 py-3 text-sm leading-relaxed resize-y placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    />
  );
}

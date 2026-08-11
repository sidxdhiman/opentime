"use client";

import { type ReactNode } from "react";

interface Props {
  title: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
}

export function SectionCard({ title, description, action, children }: Props) {
  return (
    <div className="rounded-2xl border border-border bg-card shadow-card">
      <div className="flex items-start justify-between border-b border-border/60 px-6 py-4">
        <div>
          <h2 className="font-semibold text-foreground">{title}</h2>
          {description && (
            <p className="text-xs text-muted mt-0.5">{description}</p>
          )}
        </div>
        {action && <div className="ml-4 shrink-0">{action}</div>}
      </div>
      <div className="px-6 py-5">{children}</div>
    </div>
  );
}

"use client";

import React from "react";
import { Card, CardContent } from "@/components/ui/card";

interface EmptyStateProps {
  icon: React.ElementType;
  title: string;
  description: string;
}

export function EmptyState({ icon: Icon, title, description }: EmptyStateProps) {
  return (
    <Card className="overflow-hidden">
      <CardContent className="flex flex-col items-center justify-center px-6 py-16 text-center">
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-secondary/60">
          <Icon className="h-7 w-7 text-muted" />
        </div>
        <h4 className="text-[15px] font-medium text-foreground">{title}</h4>
        <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted">{description}</p>
      </CardContent>
    </Card>
  );
}

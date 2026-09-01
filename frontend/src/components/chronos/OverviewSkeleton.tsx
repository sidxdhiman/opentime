"use client";

import React from "react";
import { Card, CardContent } from "@/components/ui/card";

function SkeletonPulse({ className }: { className?: string }) {
  return (
    <div className={`animate-pulse rounded-lg bg-secondary/40 motion-reduce:animate-none ${className || ""}`} />
  );
}

export function OverviewSkeleton() {
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6">
      <Card className="overflow-hidden">
        <CardContent className="p-6 sm:p-7">
          <div className="mb-6 flex items-center gap-3 border-b border-border/60 pb-5">
            <SkeletonPulse className="h-10 w-10 rounded-xl" />
            <div className="space-y-2">
              <SkeletonPulse className="h-4 w-32" />
              <SkeletonPulse className="h-3 w-48" />
            </div>
          </div>
          <div className="flex flex-col items-center py-8">
            <SkeletonPulse className="h-20 w-20 rounded-full" />
          </div>
          <div className="mt-4 flex justify-end">
            <SkeletonPulse className="h-10 w-28 rounded-lg" />
          </div>
        </CardContent>
      </Card>
      <div className="space-y-4">
        <SkeletonPulse className="h-24 w-full rounded-xl" />
        <SkeletonPulse className="h-24 w-full rounded-xl" />
      </div>
      <div className="space-y-6 border-t border-border/40 pt-6">
        <SkeletonPulse className="h-32 w-full rounded-xl" />
        <SkeletonPulse className="h-20 w-full rounded-xl" />
      </div>
    </div>
  );
}

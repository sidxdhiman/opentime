"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MotionConfig } from "framer-motion";
import { useState, type ReactNode } from "react";
import { AuthProvider } from "@/lib/auth";
import { MoodProvider } from "@/lib/mood";
import { MoodAmbient } from "@/components/ui/MoodAmbient";

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 60 * 1000, retry: 1 },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <MotionConfig reducedMotion="user">
        <MoodProvider>
          <AuthProvider>{children}</AuthProvider>
          <MoodAmbient />
        </MoodProvider>
      </MotionConfig>
    </QueryClientProvider>
  );
}

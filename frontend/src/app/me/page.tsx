"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  CheckCircle2,
  Cpu,
  Database,
  Loader2,
  LogOut,
  Mail,
  Palette,
  User,
  UserRound,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";
import { useMood } from "@/lib/mood";
import { MoodPicker } from "@/components/me/MoodPicker";
import { MyDataExplorer } from "@/components/my-data/MyDataExplorer";

type Section = "profile" | "data";

function initialsOf(name: string, email: string): string {
  const source = name.trim() || email.trim();
  return source
    .split(/[\s@._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
}

export default function MePage() {
  const { user, isLoading, logout } = useAuth();
  const { mood } = useMood();

  const [section, setSection] = useState<Section>("profile");

  if (isLoading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-violet-500" />
      </div>
    );
  }

  const initials = initialsOf(user.full_name ?? "", user.email);
  const name = user.full_name || user.email;
  const memberSince = new Date(user.created_at).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Header */}
      <header className="sticky top-0 z-30 border-b border-border/60 bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <Link href="/dashboard" className="flex items-center gap-1.5 text-muted hover:text-foreground transition-colors text-sm">
              <ArrowLeft className="h-4 w-4" />
              Dashboard
            </Link>
            <span className="text-border">/</span>
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-border bg-secondary text-accent-foreground">
                <UserRound className="h-3.5 w-3.5" />
              </div>
              <span className="font-semibold text-sm">Me</span>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={() => logout()} className="h-8 text-xs text-rose-400 hover:bg-rose-500/10 gap-1.5">
            <LogOut className="h-3.5 w-3.5" /> Sign out
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-8 space-y-6">
        {/* Section navigation */}
        <div className="flex gap-2 overflow-x-auto">
          <button
            type="button"
            onClick={() => setSection("profile")}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-medium rounded-lg transition-all duration-200 ${
              section === "profile"
                ? "bg-accent text-accent-foreground"
                : "text-muted hover:text-foreground hover:bg-secondary/60"
            }`}
          >
            <User className="h-4 w-4" /> Profile
          </button>
          <button
            type="button"
            onClick={() => setSection("data")}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-medium rounded-lg transition-all duration-200 ${
              section === "data"
                ? "bg-accent text-accent-foreground"
                : "text-muted hover:text-foreground hover:bg-secondary/60"
            }`}
          >
            <Database className="h-4 w-4" /> Data
          </button>
        </div>

        {section === "profile" && (
          <div className="space-y-6">
            {/* Identity card */}
            <div className="rounded-2xl border border-border bg-card shadow-card overflow-hidden">
              <div className="h-24 bg-gradient-to-r from-primary/15 via-accent/40 to-foreground/5" />
              <div className="px-6 pb-6 -mt-11">
                <div className="flex h-20 w-20 items-center justify-center rounded-2xl border-4 border-card bg-primary text-2xl font-semibold text-primary-foreground shadow-card-hover">
                  {initials || "U"}
                </div>
                <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h1 className="text-xl font-bold text-foreground">{name}</h1>
                    <p className="mt-0.5 flex items-center gap-1.5 text-sm text-muted">
                      <Mail className="h-3.5 w-3.5" /> {user.email}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {user.is_verified && (
                      <span className="flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-xs text-emerald-400">
                        <CheckCircle2 className="h-3 w-3" /> Verified
                      </span>
                    )}
                    <span className="rounded-full border border-border bg-secondary/30 px-2.5 py-0.5 text-xs text-muted">
                      {user.is_active ? "Active account" : "Disabled"}
                    </span>
                  </div>
                </div>

                <div className="mt-5 grid grid-cols-1 sm:grid-cols-3 gap-3 border-t border-border/60 pt-5">
                  <div>
                    <p className="text-[11px] uppercase tracking-wider text-muted font-semibold">Member since</p>
                    <p className="mt-0.5 text-sm text-foreground">{memberSince}</p>
                  </div>
                  <div>
                    <p className="text-[11px] uppercase tracking-wider text-muted font-semibold">User ID</p>
                    <p className="mt-0.5 text-sm text-foreground font-mono truncate">{user.id}</p>
                  </div>
                  <div>
                    <p className="text-[11px] uppercase tracking-wider text-muted font-semibold">OpenTime</p>
                    <p className="mt-0.5 flex items-center gap-1.5 text-sm text-foreground">
                      <Cpu className="h-3.5 w-3.5 text-accent-foreground" /> ChronOS profile
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Customization */}
            <div className="rounded-2xl border border-border bg-card shadow-card">
              <div className="flex items-start justify-between border-b border-border/60 px-6 py-4">
                <div>
                  <h2 className="flex items-center gap-2 font-semibold text-foreground">
                    <Palette className="h-4 w-4 text-accent-foreground" /> Customization
                  </h2>
                  <p className="text-xs text-muted mt-0.5">
                    Pick the mood of your OpenTime — the whole experience adapts to how you feel.
                  </p>
                </div>
                <span className="shrink-0 ml-4 rounded-full border border-border bg-accent px-2.5 py-0.5 text-xs text-accent-foreground">
                  {mood.emoji} {mood.name}
                </span>
              </div>
              <div className="px-6 py-5 space-y-4">
                <MoodPicker />
                <p className="text-xs text-muted/80 leading-relaxed">
                  Currently: <span className="text-foreground">{mood.name}</span> — {mood.description}
                </p>
              </div>
            </div>
          </div>
        )}

        {section === "data" && <MyDataExplorer />}
      </main>
    </div>
  );
}
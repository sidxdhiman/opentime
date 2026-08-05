import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center justify-between px-8 py-6">
        <span className="text-lg font-semibold tracking-tight">OpenTime</span>
        <nav className="flex items-center gap-3">
          <Link href="/login">
            <Button variant="ghost" size="sm">
              Sign in
            </Button>
          </Link>
          <Link href="/register">
            <Button size="sm">Get started</Button>
          </Link>
        </nav>
      </header>

      <main className="flex flex-1 flex-col items-center justify-center px-8 pb-24">
        <div className="max-w-2xl text-center">
          <h1 className="text-5xl font-semibold tracking-tight text-foreground">
            Understand how you evolve
          </h1>
          <p className="mt-6 text-lg leading-relaxed text-muted">
            OpenTime transforms your memories into structured knowledge — so you can see
            who you were, who you are, and how you changed along the way.
          </p>
          <div className="mt-10 flex items-center justify-center gap-4">
            <Link href="/register">
              <Button size="lg">Start your timeline</Button>
            </Link>
            <Link href="/login">
              <Button variant="secondary" size="lg">
                Sign in
              </Button>
            </Link>
          </div>
        </div>
      </main>

      <footer className="px-8 py-6 text-center text-sm text-muted-foreground">
        Your personal evolution engine
      </footer>
    </div>
  );
}

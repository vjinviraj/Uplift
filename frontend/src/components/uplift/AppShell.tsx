import { Bot } from "lucide-react";

import { Sidebar } from "./Sidebar";

interface AppShellProps {
  children: React.ReactNode;
  title: string;
}

export function AppShell({ children, title }: AppShellProps) {
  return (
    <div className="flex min-h-screen bg-[#09090B] text-zinc-50">
      <Sidebar />

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-zinc-800 px-5 md:px-7">
          <div className="text-sm font-semibold text-zinc-100">{title}</div>

          <div className="inline-flex items-center gap-1.5 rounded-md border border-zinc-800 bg-[#18181B] px-2.5 py-1.5 text-[11px] font-semibold text-zinc-400">
            <Bot className="h-3.5 w-3.5" strokeWidth={1.8} />
            Agentic Commerce Session
          </div>
        </header>

        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
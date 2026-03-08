"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { BarChart3, GitCompare, Layers, Code, Scissors } from "lucide-react";
import { SignedIn, UserButton } from "@clerk/nextjs";
import { HealthIndicator } from "./HealthIndicator";

const hasClerk = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.startsWith('pk_test_')
  || process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.startsWith('pk_live_');

const navItems = [
  { href: "/dashboard", label: "Evaluations", icon: BarChart3 },
  { href: "/dashboard/compare", label: "Compare Runs", icon: GitCompare },
  { href: "/dashboard/chunks", label: "Chunk Quality", icon: Scissors },
  { href: "/dashboard/api", label: "API", icon: Code },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 border-r border-slate-800 bg-slate-950 flex flex-col min-h-screen">
      <div className="p-4 border-b border-slate-800">
        <Link href="/" className="flex items-center gap-2">
          <Layers className="text-emerald-400" size={22} />
          <span className="font-bold text-lg">EvalKit</span>
        </Link>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => {
          const active =
            item.href === "/dashboard"
              ? pathname === "/dashboard" || pathname.startsWith("/dashboard/evaluation")
              : pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                active
                  ? "bg-slate-800 text-white"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/50",
              )}
            >
              <item.icon size={16} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {hasClerk && (
        <SignedIn>
          <div className="px-4 py-3 border-t border-slate-800">
            <UserButton
              appearance={{
                elements: {
                  avatarBox: "w-8 h-8",
                  userButtonPopoverCard: "bg-slate-900 border border-slate-700",
                }
              }}
              showName
            />
          </div>
        </SignedIn>
      )}

      <div className="p-4 border-t border-slate-800">
        <HealthIndicator />
      </div>
    </aside>
  );
}

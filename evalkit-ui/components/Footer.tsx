import Link from "next/link";
import { Mail } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-slate-800 py-8 px-4">
      <div className="mx-auto max-w-6xl flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex flex-col sm:flex-row items-center gap-2 sm:gap-4">
          <p className="text-sm text-slate-500">
            &copy; 2026 SriVSR. All rights reserved.
          </p>
          <a
            href="mailto:admin@srivsr.com"
            className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-300 transition-colors"
          >
            <Mail size={14} />
            admin@srivsr.com
          </a>
        </div>
        <nav className="flex items-center gap-6 text-sm text-slate-500">
          <Link href="/pricing" className="hover:text-slate-300 transition-colors">
            Pricing
          </Link>
          <Link href="/privacy" className="hover:text-slate-300 transition-colors">
            Privacy Policy
          </Link>
          <Link href="/terms" className="hover:text-slate-300 transition-colors">
            Terms of Service
          </Link>
          <Link href="/refund" className="hover:text-slate-300 transition-colors">
            Refund Policy
          </Link>
        </nav>
      </div>
    </footer>
  );
}

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Footer } from "@/components/Footer";
import { api } from "@/lib/api";
import type { LegalDocument } from "@/lib/types";

export default function PrivacyPage() {
  const [doc, setDoc] = useState<LegalDocument | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.legal.privacy().then(setDoc).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <div className="flex-1 px-4 py-16 mx-auto max-w-3xl w-full">
        <Link href="/" className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-slate-300 mb-8">
          <ArrowLeft size={14} /> Back
        </Link>
        {error && <p className="text-red-400">{error}</p>}
        {doc ? (
          <>
            <h1 className="text-3xl font-bold mb-2">{doc.title}</h1>
            <p className="text-sm text-slate-500 mb-8">Last updated: {doc.last_updated}</p>
            <div className="prose prose-invert prose-slate max-w-none whitespace-pre-wrap text-slate-300 leading-relaxed">
              {doc.content}
            </div>
          </>
        ) : (
          !error && <p className="text-slate-500">Loading...</p>
        )}
      </div>
      <Footer />
    </div>
  );
}

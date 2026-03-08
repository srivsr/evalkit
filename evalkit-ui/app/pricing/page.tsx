"use client";

import { useState } from "react";
import Link from "next/link";
import { Check, Loader2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Footer } from "@/components/Footer";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Tier {
  name: string;
  price: string;
  period: string;
  features: string[];
  cta: string;
  href?: string;
  popular?: boolean;
}

const TIERS: Tier[] = [
  {
    name: "Free",
    price: "$0",
    period: "/month",
    features: ["50 evals/month", "1 project", "Single judge model", "Community support"],
    cta: "Get Started",
    href: "/dashboard",
  },
  {
    name: "Basic",
    price: "$29",
    period: "/month",
    features: ["500 evals/month", "5 projects", "Multi-judge consensus", "Email support", "Compare & regression tracking"],
    cta: "Subscribe",
    popular: true,
  },
  {
    name: "Pro",
    price: "$99",
    period: "/month",
    features: ["Unlimited evals", "Unlimited projects", "All judge models", "Priority support", "API access", "Custom thresholds"],
    cta: "Subscribe",
  },
];

const PROVIDERS = ["paypal", "razorpay", "payoneer"] as const;

export default function PricingPage() {
  const [selectedTier, setSelectedTier] = useState<string | null>(null);
  const [provider, setProvider] = useState<typeof PROVIDERS[number]>("paypal");
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCheckout() {
    if (!selectedTier || !termsAccepted) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.payments.createOrder(selectedTier, provider, termsAccepted);
      if (res.approval_url) {
        window.location.href = res.approval_url;
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Payment failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <div className="flex-1 px-4 py-16">
        <div className="mx-auto max-w-5xl">
          <h1 className="text-4xl font-bold text-center mb-4">Pricing</h1>
          <p className="text-center text-slate-400 mb-12 max-w-xl mx-auto">
            Start free, scale as you grow. All plans include the full 6-layer evaluation pipeline.
          </p>

          <div className="grid md:grid-cols-3 gap-6 mb-16">
            {TIERS.map((tier) => (
              <Card
                key={tier.name}
                className={cn(
                  "flex flex-col",
                  tier.popular && "border-emerald-500/50 ring-1 ring-emerald-500/20"
                )}
              >
                <CardHeader>
                  {tier.popular && (
                    <span className="text-xs font-medium text-emerald-400 mb-2">Most Popular</span>
                  )}
                  <CardTitle className="text-xl">{tier.name}</CardTitle>
                  <div className="mt-2">
                    <span className="text-3xl font-bold">{tier.price}</span>
                    <span className="text-slate-400 text-sm">{tier.period}</span>
                  </div>
                </CardHeader>
                <CardContent className="flex-1">
                  <ul className="space-y-2">
                    {tier.features.map((f) => (
                      <li key={f} className="flex items-center gap-2 text-sm text-slate-300">
                        <Check size={14} className="text-emerald-400 shrink-0" />
                        {f}
                      </li>
                    ))}
                  </ul>
                </CardContent>
                <CardFooter>
                  {tier.href ? (
                    <Button asChild variant="outline" className="w-full">
                      <Link href={tier.href}>{tier.cta}</Link>
                    </Button>
                  ) : (
                    <Button
                      className={cn(
                        "w-full",
                        tier.popular
                          ? "bg-emerald-600 hover:bg-emerald-500 text-white"
                          : "bg-slate-50 text-slate-900 hover:bg-slate-50/90"
                      )}
                      onClick={() => {
                        setSelectedTier(tier.name.toLowerCase());
                        setError(null);
                      }}
                    >
                      {tier.cta}
                    </Button>
                  )}
                </CardFooter>
              </Card>
            ))}
          </div>

          {selectedTier && (
            <Card className="mx-auto max-w-lg" id="checkout">
              <CardHeader>
                <CardTitle>
                  Checkout &mdash; {selectedTier.charAt(0).toUpperCase() + selectedTier.slice(1)}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Payment Provider
                  </label>
                  <div className="flex gap-3">
                    {PROVIDERS.map((p) => (
                      <button
                        key={p}
                        onClick={() => setProvider(p)}
                        className={cn(
                          "px-4 py-2 rounded-md text-sm capitalize border transition-colors",
                          provider === p
                            ? "border-emerald-500 bg-emerald-500/10 text-emerald-400"
                            : "border-slate-700 text-slate-400 hover:border-slate-500"
                        )}
                      >
                        {p}
                      </button>
                    ))}
                  </div>
                </div>

                <label className="flex items-start gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={termsAccepted}
                    onChange={(e) => setTermsAccepted(e.target.checked)}
                    className="mt-1 accent-emerald-500"
                  />
                  <span className="text-sm text-slate-400">
                    I agree to the{" "}
                    <Link href="/terms" className="text-emerald-400 hover:underline">
                      Terms of Service
                    </Link>{" "}
                    and{" "}
                    <Link href="/privacy" className="text-emerald-400 hover:underline">
                      Privacy Policy
                    </Link>
                  </span>
                </label>

                {error && (
                  <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-md px-3 py-2">
                    {error}
                  </p>
                )}
              </CardContent>
              <CardFooter>
                <Button
                  className="w-full bg-emerald-600 hover:bg-emerald-500 text-white"
                  disabled={!termsAccepted || loading}
                  onClick={handleCheckout}
                >
                  {loading ? (
                    <>
                      <Loader2 size={16} className="animate-spin mr-2" /> Processing...
                    </>
                  ) : (
                    "Complete Payment"
                  )}
                </Button>
              </CardFooter>
            </Card>
          )}
        </div>
      </div>
      <Footer />
    </div>
  );
}

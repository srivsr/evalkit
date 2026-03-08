import { SignUp } from '@clerk/nextjs';

export default function SignUpPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 py-12 px-4">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-white">
            Join EvalKit
          </h1>
          <p className="mt-2 text-sm text-slate-400">
            Start evaluating your RAG pipelines
          </p>
        </div>
        <SignUp
          routing="path"
          path="/sign-up"
          signInUrl="/sign-in"
          fallbackRedirectUrl="/dashboard"
          appearance={{
            elements: {
              rootBox: "mx-auto",
              card: "bg-slate-900 shadow-xl rounded-lg border border-slate-800",
            }
          }}
        />
      </div>
    </div>
  );
}

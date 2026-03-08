import { SignIn } from '@clerk/nextjs';

export default function SignInPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 py-12 px-4">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-white">
            Welcome to EvalKit
          </h1>
          <p className="mt-2 text-sm text-slate-400">
            QA-Grade RAG Evaluation Platform
          </p>
        </div>
        <SignIn
          routing="path"
          path="/sign-in"
          signUpUrl="/sign-up"
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

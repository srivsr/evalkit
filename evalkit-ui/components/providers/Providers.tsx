'use client';

import { ReactNode, useEffect, useRef } from 'react';
import { ClerkProvider, useAuth as useClerkAuth } from '@clerk/nextjs';
import { dark } from '@clerk/themes';
import { setClerkToken } from '@/lib/api';

const hasValidClerkKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.startsWith('pk_test_')
  || process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.startsWith('pk_live_');

function ClerkTokenSync({ children }: { children: ReactNode }) {
  const { getToken, isSignedIn } = useClerkAuth();
  const retryRef = useRef(0);

  useEffect(() => {
    if (!isSignedIn) {
      setClerkToken(null);
      retryRef.current = 0;
      return;
    }

    let cancelled = false;

    async function syncToken() {
      try {
        const token = await getToken();
        if (!cancelled) {
          setClerkToken(token);
          retryRef.current = 0;
        }
      } catch (error) {
        console.error('Failed to get Clerk token');
        if (!cancelled) {
          setClerkToken(null);
          if (retryRef.current < 3) {
            retryRef.current++;
            const delay = 2000 * Math.pow(2, retryRef.current);
            setTimeout(() => { if (!cancelled) syncToken(); }, delay);
          }
        }
      }
    }

    syncToken();
    return () => { cancelled = true; };
  }, [isSignedIn, getToken]);

  return <>{children}</>;
}

export default function Providers({ children }: { children: ReactNode }) {
  if (!hasValidClerkKey) {
    return <>{children}</>;
  }

  return (
    <ClerkProvider appearance={{ baseTheme: dark }}>
      <ClerkTokenSync>
        {children}
      </ClerkTokenSync>
    </ClerkProvider>
  );
}

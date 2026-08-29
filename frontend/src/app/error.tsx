"use client";

import { useEffect } from "react";

/**
 * Root error boundary -- catches any otherwise-unhandled render/render-path
 * error so a bug never surfaces as Next.js's default blank/white crash
 * screen, which would look broken rather than like part of the product.
 */
export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-ink-950 px-6 text-center">
      <div className="font-mono text-[11px] tracking-kicker text-danger-pale">ERROR</div>
      <h1 className="m-0 text-[27px] font-semibold tracking-tight text-fg">Something went wrong</h1>
      <p className="m-0 max-w-[420px] text-sm text-fg-dim [text-wrap:pretty]">
        An unexpected error occurred. You can try again, or head back to your portfolio.
      </p>
      <div className="mt-2 flex gap-2.5">
        <button
          type="button"
          onClick={reset}
          className="cursor-pointer rounded-[9px] border-none bg-accent-btn px-[17px] py-[11px] font-mono text-[11px] tracking-badge text-accent-ink shadow-glow-accent transition hover:brightness-110"
        >
          TRY AGAIN
        </button>
        <a
          href="/portfolio"
          className="cursor-pointer rounded-[9px] border border-white/[0.11] bg-white/[0.03] px-4 py-2.5 font-mono text-[10.5px] tracking-badge text-fg-secondary transition hover:border-accent/40"
        >
          BACK TO PORTFOLIO
        </a>
      </div>
    </div>
  );
}

import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-ink-950 px-6 text-center">
      <div className="font-mono text-[11px] tracking-kicker text-fg-faint">404</div>
      <h1 className="m-0 text-[27px] font-semibold tracking-tight text-fg">Page not found</h1>
      <p className="m-0 max-w-[420px] text-sm text-fg-dim [text-wrap:pretty]">
        The page you're looking for doesn't exist, or you may not have access to it.
      </p>
      <Link
        href="/portfolio"
        className="mt-2 cursor-pointer rounded-[9px] border-none bg-accent-btn px-[17px] py-[11px] font-mono text-[11px] tracking-badge text-accent-ink shadow-glow-accent transition hover:brightness-110"
      >
        ← BACK TO PORTFOLIO
      </Link>
    </div>
  );
}

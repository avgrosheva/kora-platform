import { useState } from 'react';
import { FieldLabel, GhostButton, PrimaryButton } from './primitives';

export function CreateOrgModal({ open, onClose, onCreate }: {
  open: boolean;
  onClose: () => void;
  onCreate: (values: { name: string; slug?: string }) => void;
}) {
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-[60] flex items-center justify-center bg-[#030508]/75 p-6 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="kora-rise w-[min(430px,100%)] overflow-hidden rounded-2xl border border-white/[0.09] bg-gradient-to-b from-ink-850 to-ink-800 shadow-modal"
      >
        <header className="flex items-center justify-between border-b border-white/[0.07] bg-gradient-to-r from-accent/10 to-transparent px-5 py-[18px]">
          <h2 className="text-[15px] font-semibold">Create organization</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="flex h-6 w-6 cursor-pointer items-center justify-center rounded-[7px] border border-white/[0.09] bg-transparent text-[14px] text-fg-muted hover:border-white/20 hover:text-fg"
          >
            ×
          </button>
        </header>

        <div className="p-5">
          <FieldLabel>NAME</FieldLabel>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
            className="mb-[18px] w-full rounded-[9px] border border-accent/35 bg-white/[0.03] px-[13px] py-[11px] text-[14px] text-fg-secondary shadow-[0_0_22px_-12px_rgba(77,141,255,0.9)] outline-none"
          />
          <FieldLabel>SLUG <span className="text-fg-ghost">(OPTIONAL)</span></FieldLabel>
          <input
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            placeholder="auto-generated-if-empty"
            className="w-full rounded-[9px] border border-white/[0.09] bg-white/[0.025] px-[13px] py-[11px] font-mono text-[13.5px] text-fg-secondary outline-none placeholder:text-fg-disabled focus:border-accent/35"
          />
        </div>

        <footer className="flex justify-end gap-[9px] px-5 pb-5">
          <GhostButton tone="neutral" onClick={onClose}>CANCEL</GhostButton>
          <PrimaryButton onClick={() => onCreate({ name, slug: slug || undefined })}>CREATE</PrimaryButton>
        </footer>
      </div>
    </div>
  );
}

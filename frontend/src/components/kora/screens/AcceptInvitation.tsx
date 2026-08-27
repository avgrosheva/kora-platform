import { Panel, PrimaryButton } from '../primitives';

export type AcceptInvitationStatus = 'no-token' | 'pending' | 'success' | 'error';

export function AcceptInvitation({ status, errorMessage, onGoToPortfolio }: {
  status: AcceptInvitationStatus;
  errorMessage?: string | null;
  onGoToPortfolio: () => void;
}) {
  return (
    <div className="relative z-10 flex min-h-[60vh] items-center justify-center p-6">
      <Panel className="kora-rise w-full max-w-sm px-8 py-10 text-center">
        {status === 'no-token' && (
          <>
            <ErrorGlyph />
            <p className="mt-4 text-[13px] text-fg-muted">No invitation token provided.</p>
          </>
        )}

        {status === 'pending' && (
          <>
            <div className="mx-auto h-12 w-12 animate-spin rounded-full border-2 border-accent/20 border-t-accent" />
            <p className="mt-4 text-[13px] text-fg-dim">Accepting invitation…</p>
          </>
        )}

        {status === 'success' && (
          <>
            <SuccessGlyph />
            <p className="mt-4 text-[13px] text-fg-secondary">You've joined the organization.</p>
            <PrimaryButton className="mt-6" onClick={onGoToPortfolio}>GO TO PORTFOLIO</PrimaryButton>
          </>
        )}

        {status === 'error' && (
          <>
            <ErrorGlyph />
            <p className="mt-4 text-[13px] text-fg-muted [text-wrap:pretty]">{errorMessage ?? 'Could not accept invitation.'}</p>
          </>
        )}
      </Panel>
    </div>
  );
}

function ErrorGlyph() {
  return (
    <div className="relative mx-auto h-12 w-12 rounded-full border border-danger/30 bg-danger/[0.07] shadow-[0_0_40px_-14px_rgba(255,92,92,0.7)]">
      <span className="absolute left-1/2 top-1/2 h-[18px] w-0.5 -translate-x-1/2 -translate-y-1/2 rotate-45 rounded bg-danger" />
      <span className="absolute left-1/2 top-1/2 h-[18px] w-0.5 -translate-x-1/2 -translate-y-1/2 -rotate-45 rounded bg-danger" />
    </div>
  );
}

function SuccessGlyph() {
  return (
    <div className="relative mx-auto h-12 w-12 rounded-full border border-good/30 bg-good/[0.07] shadow-[0_0_40px_-14px_rgba(70,217,160,0.6)]">
      <span className="absolute left-[15px] top-[23px] h-[9px] w-0.5 rotate-45 rounded bg-good" />
      <span className="absolute left-[19px] top-[13px] h-[17px] w-0.5 -rotate-45 rounded bg-good" />
    </div>
  );
}

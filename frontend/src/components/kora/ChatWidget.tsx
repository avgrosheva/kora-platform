import { useState } from 'react';
import type { ChatMessage } from './types';
import { Badge, Tabs } from './primitives';

/**
 * Floating analyst chat. Never a route — mount once in the app shell so the
 * document context behind it is never lost.
 */
export function ChatWidget({ open, onToggle, messages, contextLabel, mode = 'ANALYTICAL', onModeToggle, unreadCount = 0, isThinking = false, suggestions = [], placeholder = 'Ask about your indexed documents…', onSend }: {
  open: boolean;
  onToggle: () => void;
  messages: ChatMessage[];
  contextLabel: string;
  mode?: string;
  /** Makes the mode badge clickable, toggling e.g. plain vs tool-calling
   * chat. Omit to render the badge as a static label. */
  onModeToggle?: () => void;
  unreadCount?: number;
  isThinking?: boolean;
  suggestions?: string[];
  placeholder?: string;
  onSend?: (text: string) => void;
}) {
  const [tab, setTab] = useState<'conversation' | 'sources'>('conversation');
  const [draft, setDraft] = useState('');

  const sources = messages.flatMap((m) => m.sources ?? []);

  if (!open) {
    return (
      <button
        type="button"
        onClick={onToggle}
        aria-label="Open Kora chat"
        className="kora-breathe fixed bottom-[26px] right-[26px] z-50 flex h-[52px] w-[52px] cursor-pointer items-center justify-center rounded-2xl border border-white/[0.14] bg-gradient-to-br from-accent-bright to-accent-deep"
      >
        <span className="font-mono text-[15px] font-semibold text-[#F2F7FF]">K</span>
        {unreadCount > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full border-2 border-ink-950 bg-danger font-mono text-[8px] text-white">
            {unreadCount}
          </span>
        )}
      </button>
    );
  }

  const submit = () => {
    if (!draft.trim()) return;
    onSend?.(draft.trim());
    setDraft('');
  };

  return (
    <div className="kora-rise fixed bottom-[26px] right-[26px] z-50 flex h-[min(560px,calc(100vh-52px))] w-[min(392px,calc(100vw-52px))] flex-col overflow-hidden rounded-2xl border border-white/[0.09] bg-gradient-to-b from-ink-850 to-ink-800 shadow-chat">
      <header className="flex shrink-0 items-center justify-between border-b border-white/[0.07] bg-gradient-to-r from-accent/10 to-transparent px-4 py-3.5">
        <div className="flex items-center gap-2.5">
          <span className="flex h-[26px] w-[26px] items-center justify-center rounded-lg bg-gradient-to-br from-accent-bright to-accent-deep font-mono text-[11px] font-semibold text-[#F2F7FF]">K</span>
          <div>
            <div className="text-[13px] font-medium">Ask Kora</div>
            <div className="font-mono text-[9px] tracking-badge text-fg-dim">CONTEXT · {contextLabel}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {onModeToggle ? (
            <button type="button" onClick={onModeToggle} className="cursor-pointer border-none bg-transparent p-0">
              <Badge tone="accent">{mode}</Badge>
            </button>
          ) : (
            <Badge tone="accent">{mode}</Badge>
          )}
          <button
            type="button"
            onClick={onToggle}
            aria-label="Collapse chat"
            className="flex h-6 w-6 cursor-pointer items-center justify-center rounded-[7px] border border-white/[0.09] bg-transparent text-[13px] text-fg-muted transition-colors hover:border-white/20 hover:text-fg"
          >
            ×
          </button>
        </div>
      </header>

      <div className="shrink-0 px-3">
        <Tabs
          size="sm"
          active={tab}
          onSelect={setTab}
          tabs={[
            { id: 'conversation', label: 'Conversation' },
            { id: 'sources', label: 'Sources', hint: String(sources.length) },
          ]}
        />
      </div>

      <div className="flex flex-1 flex-col gap-3.5 overflow-y-auto p-4">
        {tab === 'conversation' ? (
          <>
            {messages.map((m) =>
              m.role === 'user' ? (
                <div key={m.id} className="max-w-[78%] self-end rounded-[12px_12px_4px_12px] border border-accent/[0.26] bg-accent/[0.14] px-[13px] py-2.5 text-[12.5px] text-fg-secondary">
                  {m.text}
                </div>
              ) : (
                <div key={m.id} className="flex max-w-[88%] flex-col gap-[9px]">
                  <div className="rounded-[12px_12px_12px_4px] border border-white/[0.07] bg-white/[0.03] px-[13px] py-[11px] text-[12.5px] leading-relaxed text-fg-tertiary [text-wrap:pretty]">
                    {m.text}
                  </div>
                  {!!m.sources?.length && (
                    <div className="flex flex-wrap gap-1.5">
                      {m.sources.map((s) => (
                        <span key={s.label} className="rounded-full border border-white/[0.09] bg-white/[0.035] px-2 py-1 font-mono text-[9px] text-fg-quiet">
                          {s.label}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )
            )}
            {isThinking && (
              <div className="flex items-center gap-[7px] font-mono text-[10px] text-fg-dim">
                <span className="kora-blink-fast h-[5px] w-[5px] rounded-full bg-accent-bright" />
                READING {sources.length} SOURCES…
              </div>
            )}
          </>
        ) : (
          <div className="flex flex-col gap-2">
            {sources.length === 0 && <div className="text-xs text-fg-faint">No sources cited yet.</div>}
            {sources.map((s, i) => (
              <div key={s.label + i} className="rounded-lg border border-white/[0.07] bg-white/[0.02] px-3 py-2.5 font-mono text-[11px] text-fg-quiet">
                {s.label}
              </div>
            ))}
          </div>
        )}
      </div>

      <footer className="shrink-0 border-t border-white/[0.07] px-3.5 pb-3.5 pt-3">
        {!!suggestions.length && (
          <div className="mb-2.5 flex flex-wrap gap-1.5">
            {suggestions.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => onSend?.(s)}
                className="cursor-pointer rounded-full border border-white/[0.08] bg-white/[0.025] px-[9px] py-[5px] text-[11px] text-fg-quiet transition-colors hover:border-accent/35 hover:text-fg-secondary"
              >
                {s}
              </button>
            ))}
          </div>
        )}
        <div className="flex items-center gap-2.5 rounded-[10px] border border-white/[0.09] bg-white/[0.025] px-3 py-2.5 focus-within:border-accent/45">
          <span className="font-mono text-xs text-accent">›</span>
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') submit(); }}
            placeholder={placeholder}
            className="min-w-0 flex-1 border-none bg-transparent text-[12.5px] text-fg outline-none placeholder:text-fg-faint"
          />
          <span className="font-mono text-[9px] text-fg-disabled">⏎</span>
        </div>
      </footer>
    </div>
  );
}

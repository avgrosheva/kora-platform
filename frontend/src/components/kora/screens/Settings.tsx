import { useState } from 'react';
import type { Organization } from '../types';
import { FieldLabel, GhostButton, PageHeading, Panel, PanelHeader } from '../primitives';

export function Settings({ organization, onSave, onDelete }: {
  organization: Organization;
  onSave: (values: { name: string; slug: string }) => void;
  onDelete: () => void;
}) {
  const [name, setName] = useState(organization.name);
  const [slug, setSlug] = useState(organization.slug);

  const field = 'w-full rounded-[9px] border border-white/[0.09] bg-white/[0.025] px-[13px] py-[11px] text-[13px] text-fg-secondary outline-none transition-colors focus:border-accent/35';

  return (
    <div className="relative z-10 max-w-[820px] px-9 pb-24 pt-10">
      <PageHeading
        kicker={'SETTINGS / ' + organization.name.toUpperCase()}
        title="Settings"
        blurb="Organization details and destructive actions."
      />

      <Panel className="kora-rise kora-d1 mb-[18px] overflow-hidden">
        <PanelHeader title="Organization details" />
        <div className="grid grid-cols-2 gap-[18px] p-[22px]">
          <div>
            <FieldLabel>NAME</FieldLabel>
            <input value={name} onChange={(e) => setName(e.target.value)} className={field} />
          </div>
          <div>
            <FieldLabel>SLUG</FieldLabel>
            <input value={slug} onChange={(e) => setSlug(e.target.value)} className={field + ' font-mono !text-[12.5px]'} />
          </div>
        </div>
        <div className="flex justify-end px-[22px] pb-5">
          <GhostButton tone="neutral" onClick={() => onSave({ name, slug })}>SAVE CHANGES</GhostButton>
        </div>
      </Panel>

      <section className="kora-rise kora-d2 rounded-[14px] border border-danger/[0.22] bg-gradient-to-b from-danger/[0.05] to-white/[0.008] p-[22px]">
        <div className="mb-2.5 flex items-center gap-[9px]">
          <span className="h-1.5 w-1.5 rounded-full bg-danger shadow-[0_0_10px_2px_rgba(255,92,92,0.7)]" />
          <span className="font-mono text-[10px] tracking-label text-danger-soft">DANGER ZONE</span>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-5">
          <p className="m-0 max-w-[440px] text-[12.5px] text-fg-muted [text-wrap:pretty]">
            Permanently delete this organization, its members, and all its documents. This cannot be undone.
          </p>
          <GhostButton tone="danger" onClick={onDelete}>DELETE ORGANIZATION</GhostButton>
        </div>
      </section>
    </div>
  );
}

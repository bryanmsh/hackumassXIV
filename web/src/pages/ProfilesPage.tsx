import { useState } from 'react';
import { api } from '../api';
import { ProfileEditor } from '../components/profiles/ProfileEditor';
import { PageHeader } from '../components/ui/AppShell';
import { Button } from '../components/ui/Button';
import { EmptyState, ErrorPanel, Loading } from '../components/ui/LoadState';
import { useApi } from '../hooks/useApi';
import type { Profile } from '../types/api';
import { levelName } from '../utils/display';
import { POSITIONS, SIZES, backgroundName, lowContrast, swatchName } from '../utils/profiles';

type Editing = { kind: 'new' } | { kind: 'edit'; profile: Profile } | null;

/** Child profiles: list, create and edit, with a live preview of unsaved settings. */
export function ProfilesPage() {
  const profiles = useApi((signal) => api.listProfiles(signal), 'profiles');
  const [editing, setEditing] = useState<Editing>(null);
  const [notice, setNotice] = useState<string | null>(null);

  function open(next: Editing) {
    setNotice(null);
    setEditing(next);
  }

  return (
    <>
      <PageHeader title="Child profiles">
        {!editing && (
          <Button variant="primary" onClick={() => open({ kind: 'new' })}>
            New child profile
          </Button>
        )}
      </PageHeader>
      <p className="mb-6 max-w-3xl text-slate-700">
        A profile holds the display choices you make for one child. The looks are presentation modes, not stages, and Mirai
        never assesses a child or recommends a look.
      </p>

      {notice && (
        <p role="status" className="mb-4 rounded-lg bg-emerald-50 p-3 text-emerald-950 ring-1 ring-emerald-200">
          {notice}
        </p>
      )}

      {editing && (
        <div className="mb-8">
          <ProfileEditor
            key={editing.kind === 'edit' ? editing.profile.id : 'new'}
            profile={editing.kind === 'edit' ? editing.profile : undefined}
            onCancel={() => setEditing(null)}
            onSaved={(p, created) => {
              setEditing(null);
              setNotice(created ? `${p.name}’s profile was created.` : `${p.name}’s profile was saved.`);
              profiles.reload();
            }}
          />
        </div>
      )}

      {profiles.status === 'loading' && <Loading label="Loading profiles…" />}
      {profiles.status === 'error' && <ErrorPanel error={profiles.error} onRetry={profiles.reload} title="Could not load profiles" />}
      {profiles.data && profiles.data.length === 0 && !editing && (
        <EmptyState title="No child profiles yet">Create one to choose how pages are shown to a child.</EmptyState>
      )}
      {profiles.data && profiles.data.length > 0 && (
        <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" aria-label="Profiles">
          {profiles.data.map((p) => (
            <li key={p.id} className="flex flex-col rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
              <h2 className="text-xl font-bold">{p.name}</h2>
              <p className="mt-1 text-slate-700">Look: {levelName(p.level)}</p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                {p.settings.colors.map((c, i) => (
                  <span key={`${c}-${i}`} className="inline-flex items-center gap-2 rounded-full bg-slate-100 py-1 pl-1 pr-3 text-sm">
                    <span className="size-6 rounded-full ring-1 ring-slate-400" style={{ backgroundColor: c }} aria-hidden />
                    {swatchName(c)}
                    {i === 0 && ' (main)'}
                  </span>
                ))}
                <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 py-1 pl-1 pr-3 text-sm">
                  <span className="size-6 rounded ring-1 ring-slate-400" style={{ backgroundColor: p.settings.background }} aria-hidden />
                  Background: {backgroundName(p.settings.background)}
                </span>
              </div>
              <p className="mt-2 text-sm text-slate-700">
                {SIZES.find((s) => s.value === p.settings.size)?.name ?? p.settings.size} ·{' '}
                {POSITIONS.find((o) => o.value === p.settings.position)?.name ?? p.settings.position} · text{' '}
                {p.settings.text_mode === 'below' ? 'below the picture' : 'off (words not shown)'}
              </p>
              {lowContrast({ colors: p.settings.colors, background: p.settings.background }) && (
                <p className="mt-2 text-sm text-amber-900">
                  Low contrast kept{p.contrast_override_note ? `: “${p.contrast_override_note}”` : '.'}
                </p>
              )}
              <div className="mt-auto pt-4">
                <Button disabled={editing !== null} onClick={() => open({ kind: 'edit', profile: p })} aria-label={`Edit ${p.name}`}>
                  Edit
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

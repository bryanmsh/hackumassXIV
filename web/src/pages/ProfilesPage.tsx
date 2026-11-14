import { api } from '../api';
import { PageHeader } from '../components/ui/AppShell';
import { EmptyState, ErrorPanel, Loading } from '../components/ui/LoadState';
import { useApi } from '../hooks/useApi';
import { BACKGROUNDS, SWATCHES, levelName } from '../utils/display';

const swatchName = (hex: string) => SWATCHES.find((s) => s.hex.toUpperCase() === hex.toUpperCase())?.name ?? hex;
const backgroundName = (hex: string) => BACKGROUNDS.find((b) => b.hex.toUpperCase() === hex.toUpperCase())?.name ?? hex;

// D1 shell: lists profiles from GET /profiles. Create/edit, live preview and contrast warning are D4.
export function ProfilesPage() {
  const profiles = useApi((signal) => api.listProfiles(signal), 'profiles');

  return (
    <>
      <PageHeader title="Child profiles" />
      <p className="mb-6 max-w-3xl text-slate-700">
        A profile holds the display choices you make for one child. The looks are presentation modes, not stages, and
        Mirai never assesses a child or recommends a look.
      </p>
      {profiles.status === 'loading' && <Loading label="Loading profiles…" />}
      {profiles.status === 'error' && <ErrorPanel error={profiles.error} onRetry={profiles.reload} />}
      {profiles.data && profiles.data.length === 0 && <EmptyState title="No child profiles yet" />}
      {profiles.data && profiles.data.length > 0 && (
        <ul className="grid gap-4 md:grid-cols-2">
          {profiles.data.map((p) => (
            <li key={p.id} className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
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
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

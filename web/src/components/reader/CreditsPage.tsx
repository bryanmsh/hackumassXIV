import type { ReaderManifest } from '../../types/api';
import { luminance } from '../../utils/contrast';

/** The last page of every reading: the book's credits and the adaptation notice. */
export function CreditsPage({ manifest, background }: { manifest: ReaderManifest; background: string }) {
  const dark = (luminance(background) ?? 0) < 0.4;
  const c = manifest.credits;
  const rows: [string, string | null][] = [
    ['Author', c.author],
    ['Illustrator', c.illustrator],
    ['Publisher', c.publisher],
    ['Source', c.source],
    ['License', c.license],
  ];
  return (
    <section
      aria-label="Credits"
      className={`flex h-full w-full flex-col items-center justify-center gap-6 p-10 text-center ${dark ? 'text-white' : 'text-slate-950'}`}
    >
      <h1 className="text-4xl font-bold sm:text-5xl">{manifest.title}</h1>
      <dl className="space-y-2 text-xl sm:text-2xl">
        {rows
          .filter(([, v]) => v)
          .map(([k, v]) => (
            <div key={k}>
              <dt className="inline font-bold">{k}: </dt>
              <dd className="inline break-words">{v}</dd>
            </div>
          ))}
      </dl>
      <p className="max-w-3xl text-lg sm:text-xl">{manifest.adaptation_note}</p>
    </section>
  );
}

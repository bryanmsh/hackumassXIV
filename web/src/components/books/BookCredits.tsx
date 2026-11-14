import { Fragment, useId, useState, type FormEvent } from 'react';
import { api } from '../../api';
import { useAction } from '../../hooks/useAction';
import type { Book, Credits } from '../../types/api';
import { CREDIT_FIELDS, type CreditsDraft } from '../../utils/upload';
import { Button } from '../ui/Button';
import { errorMessage } from '../ui/LoadState';

const inputClass =
  'mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base text-slate-900 shadow-sm focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-600/30';

/**
 * A book's five credits on its Library card. The server fills them from the PDF
 * at upload where it can; what it could not find reads "Not found", so the
 * teacher knows to type it. Edit saves through PATCH /books/{id} {credits}.
 */
export function BookCredits({ book, onSaved }: { book: Book; onSaved: () => void }) {
  const [editing, setEditing] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const missing = CREDIT_FIELDS.filter((f) => !book.credits[f.key]).length;

  if (editing) {
    return (
      <CreditsForm
        book={book}
        onCancel={() => setEditing(false)}
        onSaved={() => {
          setEditing(false);
          setNotice('Credits saved.');
          onSaved();
        }}
      />
    );
  }

  return (
    <section className="mt-3" aria-label={`Credits of ${book.title}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-700">Credits</h3>
        <Button
          onClick={() => {
            setNotice(null);
            setEditing(true);
          }}
          aria-label={`Edit credits of ${book.title}`}
        >
          Edit credits
        </Button>
      </div>
      <dl className="mt-1 grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-sm">
        {CREDIT_FIELDS.map(({ key, label }) => (
          <Fragment key={key}>
            <dt className="text-slate-600">{label}</dt>
            <dd className="break-words">{book.credits[key] ?? <span className="text-amber-900">Not found</span>}</dd>
          </Fragment>
        ))}
      </dl>
      {missing > 0 && (
        <p className="mt-1 text-sm text-slate-600">Read from the PDF where possible. Type anything marked “Not found” with Edit credits.</p>
      )}
      {notice && (
        <p role="status" className="mt-1 text-sm text-emerald-900">
          {notice}
        </p>
      )}
    </section>
  );
}

function draftOf(c: Credits): CreditsDraft {
  return { author: c.author ?? '', illustrator: c.illustrator ?? '', publisher: c.publisher ?? '', source: c.source ?? '', license: c.license ?? '' };
}

function CreditsForm({ book, onCancel, onSaved }: { book: Book; onCancel: () => void; onSaved: () => void }) {
  const ids = useId();
  const [draft, setDraft] = useState<CreditsDraft>(() => draftOf(book.credits));
  const save = useAction();

  async function submit(e: FormEvent) {
    e.preventDefault();
    // All five keys every time: a cleared field is saved as empty, not left as it was.
    const credits: Credits = { author: null, illustrator: null, publisher: null, source: null, license: null };
    for (const { key } of CREDIT_FIELDS) credits[key] = draft[key].trim() || null;
    const saved = await save.run('save', (s) => api.updateBook(book.id, { credits }, s));
    if (saved) onSaved();
  }

  return (
    <form onSubmit={submit} noValidate aria-labelledby={`${ids}-h`} className="mt-3 rounded-lg bg-slate-50 p-3 ring-1 ring-inset ring-slate-200">
      <h3 id={`${ids}-h`} className="text-sm font-semibold text-slate-700">
        Edit credits of {book.title}
      </h3>
      <div className="mt-2 grid gap-3 sm:grid-cols-2">
        {CREDIT_FIELDS.map(({ key, label }) => (
          <div key={key}>
            <label htmlFor={`${ids}-${key}`} className="font-semibold">
              {label}
            </label>
            <input
              id={`${ids}-${key}`}
              className={inputClass}
              value={draft[key]}
              autoComplete="off"
              onChange={(e) => setDraft((d) => ({ ...d, [key]: e.target.value }))}
            />
          </div>
        ))}
      </div>
      {save.error && (
        <p role="alert" className="mt-3 rounded-lg bg-rose-50 p-3 text-rose-900 ring-1 ring-rose-200">
          Not saved: {errorMessage(save.error)}
        </p>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        <Button type="submit" variant="primary" disabled={save.pending !== null}>
          {save.pending ? 'Saving…' : 'Save credits'}
        </Button>
        <Button onClick={onCancel} disabled={save.pending !== null}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

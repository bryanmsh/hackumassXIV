import { NavLink, Outlet } from 'react-router';
import { MOCKS_ENABLED, describeApiTarget } from '../../config';
import { MockBanner } from './MockBanner';

const navClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-lg px-3 py-2 text-base font-semibold ${isActive ? 'bg-sky-100 text-sky-900' : 'text-slate-700 hover:bg-slate-100'}`;

/** Teacher-facing layout. The Reader is rendered outside this shell. */
export function AppShell() {
  return (
    <div className="flex min-h-screen flex-col">
      {MOCKS_ENABLED && <MockBanner />}
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-4 px-4 py-3 sm:px-6">
          <NavLink to="/" className="text-2xl font-bold tracking-tight text-slate-900">
            Mirai
          </NavLink>
          <nav aria-label="Main" className="flex gap-1">
            <NavLink to="/" end className={navClass}>
              Library
            </NavLink>
            <NavLink to="/profiles" className={navClass}>
              Child profiles
            </NavLink>
          </nav>
          {import.meta.env.DEV && (
            <span className="ml-auto rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-600" title="Set by VITE_API_URL">
              {describeApiTarget()}
            </span>
          )}
        </div>
      </header>
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6">
        <Outlet />
      </main>
    </div>
  );
}

export function PageHeader({ title, children, back }: { title: string; children?: React.ReactNode; back?: React.ReactNode }) {
  return (
    <div className="mb-6">
      {back && <div className="mb-2">{back}</div>}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
        {children && <div className="flex flex-wrap gap-2">{children}</div>}
      </div>
    </div>
  );
}

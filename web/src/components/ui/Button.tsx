import type { ButtonHTMLAttributes } from 'react';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-sky-700 text-white hover:bg-sky-800 disabled:bg-slate-300 disabled:text-slate-600',
  secondary:
    'bg-white text-slate-900 ring-1 ring-inset ring-slate-300 hover:bg-slate-100 disabled:text-slate-400 disabled:hover:bg-white',
  danger: 'bg-white text-rose-800 ring-1 ring-inset ring-rose-300 hover:bg-rose-50 disabled:text-slate-400',
  ghost: 'text-sky-800 hover:bg-sky-50 disabled:text-slate-400',
};

export function Button({
  variant = 'secondary',
  className = '',
  type = 'button',
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      type={type}
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2 text-base font-semibold transition-colors disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`}
      {...rest}
    />
  );
}

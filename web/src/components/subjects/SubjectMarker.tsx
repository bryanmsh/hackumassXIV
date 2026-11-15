import { subjectNumber, subjectTone } from '../../utils/subjectColors';

/**
 * A suggestion's badge: its colour with its number inside, and a 2 px white edge so
 * it holds up on any illustration. Decorative on its own; the control it sits in
 * carries the accessible name.
 */
export function SubjectMarker({ index, size = 'md', className = '' }: { index: number; size?: 'sm' | 'md'; className?: string }) {
  const t = subjectTone(index);
  return (
    <span
      aria-hidden
      data-testid="subject-marker"
      data-subject={subjectNumber(index)}
      className={`inline-flex shrink-0 items-center justify-center rounded-full border-2 border-white font-bold tabular-nums shadow-[0_0_0_1px_rgba(0,0,0,0.45)] ${
        size === 'md' ? 'size-8 text-base' : 'size-6 text-sm'
      } ${t.fill} ${t.ink} ${className}`}
    >
      {subjectNumber(index)}
    </span>
  );
}

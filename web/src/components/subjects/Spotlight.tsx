import type { NormBox } from '../../types/api';
import { boxToPercent } from '../../utils/coordinates';
import { subjectTone } from '../../utils/subjectColors';

/**
 * Emphasis for one suggestion while the teacher points at its chip or row: the rest of
 * the picture darkens and the suggestion's area keeps a border in its colour. Shown only
 * on hover or focus, so nothing sits on the artwork at rest. Positioned inside a frame
 * that covers exactly the drawn page.
 */
export function Spotlight({ box, index }: { box: NormBox; index: number }) {
  return (
    <span
      data-testid="spotlight"
      data-subject={index + 1}
      aria-hidden
      className={`pointer-events-none absolute rounded-sm border-[3px] ${subjectTone(index).border} shadow-[0_0_0_2px_#fff,0_0_0_9999px_rgba(15,23,42,0.45)]`}
      style={boxToPercent(box)}
    />
  );
}

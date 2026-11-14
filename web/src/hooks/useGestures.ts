import { useEffect, useMemo, useRef, type PointerEvent as ReactPointerEvent } from 'react';
import { GestureRecognizer, type Gesture, type GestureOptions } from '../utils/gestures';

/**
 * Pointer handlers for a gesture surface (the Reader page, or the device test
 * page). Spread `handlers` onto ONE element and add `className` to it: that
 * sets `touch-action: none` on that element only, so the browser does not
 * scroll, zoom or navigate there, and nowhere else.
 */
export function useGestures(onGesture: (g: Gesture) => void, opts: Partial<GestureOptions> = {}) {
  const handler = useRef(onGesture);
  handler.current = onGesture;
  // Options are compared by value, so an inline object does not rebuild the recognizer.
  const optsKey = JSON.stringify(opts);
  const recognizer = useMemo(() => new GestureRecognizer((g) => handler.current(g), opts), [optsKey]);

  useEffect(() => () => recognizer.reset(), [recognizer]);

  const sample = (e: ReactPointerEvent) => ({ id: e.pointerId, x: e.clientX, y: e.clientY, t: e.timeStamp });

  const handlers = {
    onPointerDown(e: ReactPointerEvent<HTMLElement>) {
      const r = e.currentTarget.getBoundingClientRect();
      try {
        e.currentTarget.setPointerCapture(e.pointerId);
      } catch {
        // Capture is a nicety; the gesture still works without it.
      }
      recognizer.down({ ...sample(e), x: e.clientX - r.left, y: e.clientY - r.top }, r.width, r.height);
    },
    onPointerMove(e: ReactPointerEvent<HTMLElement>) {
      const r = e.currentTarget.getBoundingClientRect();
      recognizer.move({ ...sample(e), x: e.clientX - r.left, y: e.clientY - r.top });
    },
    onPointerUp(e: ReactPointerEvent<HTMLElement>) {
      const r = e.currentTarget.getBoundingClientRect();
      recognizer.up({ ...sample(e), x: e.clientX - r.left, y: e.clientY - r.top });
    },
    onPointerCancel(e: ReactPointerEvent<HTMLElement>) {
      recognizer.cancel({ id: e.pointerId });
    },
    // Stop the long-press context menu / text selection callout on the surface.
    onContextMenu(e: React.MouseEvent) {
      e.preventDefault();
    },
  };
  return { handlers, className: 'touch-none select-none' };
}

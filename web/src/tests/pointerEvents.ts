/**
 * jsdom has no PointerEvent, so fireEvent.pointerDown would send a plain Event
 * with no position. This minimal stand-in carries what the editor reads:
 * clientX/Y (from MouseEvent), pointerId, isPrimary and pointerType. Tests only.
 */
if (typeof window !== 'undefined' && !('PointerEvent' in window)) {
  class TestPointerEvent extends MouseEvent {
    readonly pointerId: number;
    readonly isPrimary: boolean;
    readonly pointerType: string;
    readonly pressure: number;
    constructor(type: string, init: PointerEventInit = {}) {
      super(type, init);
      this.pointerId = init.pointerId ?? 1;
      this.isPrimary = init.isPrimary ?? true;
      this.pointerType = init.pointerType ?? 'mouse';
      this.pressure = init.pressure ?? 0.5;
    }
  }
  Object.defineProperty(window, 'PointerEvent', { value: TestPointerEvent, configurable: true });
}

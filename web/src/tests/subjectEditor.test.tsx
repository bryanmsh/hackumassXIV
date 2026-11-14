/**
 * Subject editor: candidate pick, tap-to-pick and freehand outline send the
 * agreed bodies with 0-1 positions measured against the drawn image only.
 * jsdom has no layout, so the image frame's on-screen rectangle is set here.
 */
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http } from 'msw';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '../App';
import { api } from '../api';
import { scenarios } from '../mocks/db';
import { server } from '../mocks/node';
import type { Book, NormPoint } from '../types/api';
import { MAX_OUTLINE_POINTS } from '../utils/coordinates';

/** Where the page image is drawn on screen in these tests (client px). */
const FRAME = { left: 100, top: 50, width: 800, height: 600 };
const at = ([x, y]: NormPoint) => ({ clientX: FRAME.left + x * FRAME.width, clientY: FRAME.top + y * FRAME.height });

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
    const r = this.dataset.testid === 'image-frame' ? FRAME : { left: 0, top: 0, width: 0, height: 0 };
    return { ...r, x: r.left, y: r.top, right: r.left + r.width, bottom: r.top + r.height, toJSON: () => r } as DOMRect;
  });
});

function captureSubjectBodies(): unknown[] {
  const bodies: unknown[] = [];
  server.use(
    http.post('*/api/pages/:id/subject', async ({ request }) => {
      bodies.push(await request.clone().json());
      return undefined;
    }),
  );
  return bodies;
}

async function openPage(n: number) {
  const demo: Book = (await api.listBooks()).find((b) => b.title.startsWith('Animal Homes'))!;
  const page = demo.pages.find((p) => p.number === n)!;
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={[`/pages/${page.id}?book=${demo.id}`]}>
      <App />
    </MemoryRouter>,
  );
  const frame = await screen.findByTestId('image-frame');
  return { user, page, frame, demo };
}

function circle(n: number, c: NormPoint = [0.5, 0.5], r = 0.25): NormPoint[] {
  return Array.from({ length: n }, (_, i) => {
    const a = (i / n) * Math.PI * 2;
    return [c[0] + r * Math.cos(a), c[1] + r * Math.sin(a)] as NormPoint;
  });
}

function draw(frame: HTMLElement, pts: NormPoint[], opts: { pointerId?: number; isPrimary?: boolean } = {}) {
  const base = { pointerId: opts.pointerId ?? 1, isPrimary: opts.isPrimary ?? true, pointerType: 'touch', button: 0 };
  fireEvent.pointerDown(frame, { ...base, ...at(pts[0]!) });
  for (const p of pts.slice(1)) fireEvent.pointerMove(frame, { ...base, ...at(p) });
  fireEvent.pointerUp(frame, { ...base, ...at(pts[pts.length - 1]!) });
}

describe('Subject editor', () => {
  it('shows candidate boxes over the page; picking one sends {candidate: index}', async () => {
    const { user } = await openPage(3);
    const bodies = captureSubjectBodies();
    const box = screen.getByRole('button', { name: /^Pick beehive/ });
    expect(box).toHaveStyle({ left: '44.000%', top: '12.000%' });
    await user.click(box);
    expect(await screen.findByText(/Subject changed to “beehive”/)).toBeInTheDocument();
    expect(bodies).toEqual([{ candidate: 1 }]);
    expect(screen.getByRole('button', { name: /Current subject beehive/ })).toBeInTheDocument();
  });

  it('ticking two suggestions and Show together sends {candidates: [...]} and selects the joined subject', async () => {
    const { user } = await openPage(3);
    const bodies = captureSubjectBodies();
    expect(screen.queryByRole('button', { name: /Show these/ })).not.toBeInTheDocument();
    const boxes = screen.getAllByRole('checkbox', { name: /^Include / });
    await user.click(boxes[1]!);
    expect(screen.getByText(/Tick one more/)).toBeInTheDocument();
    await user.click(boxes[0]!);
    await user.click(screen.getByRole('button', { name: 'Show these 2 together' }));
    expect(await screen.findByText(/together\. Check the highlight/)).toBeInTheDocument();
    expect(bodies).toEqual([{ candidates: [0, 1] }]);
    expect(screen.getAllByText(/ and beehive|beehive and /).length).toBeGreaterThan(0);
  });

  it('tick boxes have a 44 px target and clear when the subject changes; joined subjects say "made by teacher"', async () => {
    const { user } = await openPage(3);
    const boxes = screen.getAllByRole('checkbox', { name: /^Include / });
    expect(boxes[0]!.closest('label')).toHaveClass('size-11');
    await user.click(boxes[0]!);
    await user.click(boxes[1]!);
    expect(screen.getByRole('button', { name: 'Show these 2 together' })).toBeInTheDocument();
    // Picking a single suggestion instead changes the subject and drops the ticks.
    await user.click(screen.getByRole('button', { name: /^Pick nest/ }));
    await screen.findByText(/Subject changed to “nest”/);
    expect(screen.getAllByRole('checkbox', { name: /^Include / }).every((b) => !(b as HTMLInputElement).checked)).toBe(true);
    expect(screen.queryByRole('button', { name: /Show these/ })).not.toBeInTheDocument();
    // Joining two shows "made by teacher", never "outlined by teacher".
    const again = screen.getAllByRole('checkbox', { name: /^Include / });
    await user.click(again[0]!);
    await user.click(again[1]!);
    await user.click(screen.getByRole('button', { name: 'Show these 2 together' }));
    await screen.findByText(/together\. Check the highlight/);
    expect(screen.getAllByText(/made by teacher/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/outlined by teacher/)).not.toBeInTheDocument();
  });

  it('add a missing part: sends {refine_point} for the current subject, which keeps its name', async () => {
    const { user, frame } = await openPage(1); // page 1 has a selected subject (weaver bird)
    const bodies = captureSubjectBodies();
    await user.click(screen.getByRole('button', { name: 'Add a missing part' }));
    expect(screen.getByText(/that the cut-out missed/)).toHaveTextContent('weaver bird');
    expect(screen.getByRole('button', { name: 'Add this part' })).toBeDisabled();
    fireEvent.click(frame, at([0.7, 0.3]));
    await user.click(screen.getByRole('button', { name: 'Add this part' }));
    expect(await screen.findByText(/Added the part you clicked/)).toBeInTheDocument();
    expect(bodies).toEqual([{ refine_point: [0.7, 0.3] }]);
    expect(screen.getByText(/Current subject/).closest('section')).toHaveTextContent('weaver bird');
    expect(screen.getByTestId('sent-marker')).toBeInTheDocument();
  });

  it('add a missing part needs a subject first; switching tools clears the spot', async () => {
    const { user, frame } = await openPage(3); // nothing selected yet
    await user.click(screen.getByRole('button', { name: 'Add a missing part' }));
    expect(screen.getByText('Pick a subject first. Then this adds any part the cut-out missed.')).toBeInTheDocument();
    fireEvent.click(frame, at([0.5, 0.5]));
    expect(screen.getByRole('button', { name: 'Add this part' })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Click the object' }));
    expect(screen.queryByTestId('tap-marker')).not.toBeInTheDocument();
  });

  it('click the object: the 0-1 spot inside the drawn image is sent only after Cut out', async () => {
    const { user, frame } = await openPage(3);
    const bodies = captureSubjectBodies();
    await user.click(screen.getByRole('button', { name: 'Click the object' }));
    fireEvent.click(frame, at([0.25, 0.4]));
    expect(screen.getByTestId('tap-marker')).toHaveStyle({ left: '25%', top: '40%' });
    expect(bodies).toHaveLength(0);

    await user.click(screen.getByRole('button', { name: 'Cut out the object here' }));
    expect(await screen.findByText(/Cut out where you clicked/)).toBeInTheDocument();
    expect(bodies).toEqual([{ point: [0.25, 0.4] }]);
    expect(screen.getByText(/picked by clicking/)).toBeInTheDocument();
    expect(screen.getByTestId('sent-marker')).toBeInTheDocument();
  });

  it('a click on the letterboxing outside the image is not accepted', async () => {
    const { user, frame } = await openPage(3);
    await user.click(screen.getByRole('button', { name: 'Click the object' }));
    fireEvent.click(frame, { clientX: FRAME.left - 5, clientY: FRAME.top + 100 });
    expect(screen.getByRole('alert')).toHaveTextContent('Click on the picture itself.');
    expect(screen.queryByTestId('tap-marker')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cut out the object here' })).toBeDisabled();
  });

  it('outline: a long stroke is thinned to ≤ 200 points in 0..1 and sent with its label', async () => {
    const { user, frame } = await openPage(4);
    const bodies = captureSubjectBodies();
    expect(frame).toHaveClass('touch-manipulation');
    await user.click(screen.getByRole('button', { name: 'Draw an outline' }));
    // Only the drawing surface stops the page from scrolling, and only while drawing is possible.
    expect(frame).toHaveClass('touch-none');
    expect(document.body.querySelectorAll('.touch-none')).toHaveLength(1);
    await user.type(screen.getByLabelText('What is it?'), 'termite mound');
    draw(frame, circle(600, [0.6, 0.55], 0.2));
    expect(screen.getByText(/Outline ready/)).toBeInTheDocument();
    expect(screen.getByTestId('drawn-outline')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Save outline' }));
    expect(await screen.findByText(/cut out along your outline/)).toBeInTheDocument();
    const body = bodies[0] as { label: string; outline: NormPoint[] };
    expect(Object.keys(body).sort()).toEqual(['label', 'outline']);
    expect(body.label).toBe('termite mound');
    expect(body.outline.length).toBeGreaterThanOrEqual(3);
    expect(body.outline.length).toBeLessThanOrEqual(MAX_OUTLINE_POINTS);
    for (const [x, y] of body.outline) {
      expect(x >= 0 && x <= 1 && y >= 0 && y <= 1).toBe(true);
      // Same shape in page fractions as drawn on screen (not screen pixels, not master pixels).
      expect(Math.abs(Math.hypot(x - 0.6, y - 0.55) - 0.2)).toBeLessThan(0.01);
    }
    expect(body.outline[0]).not.toEqual(body.outline[body.outline.length - 1]);
    expect(screen.getByText(/made by teacher/)).toBeInTheDocument();
    expect(screen.getByTestId('sent-outline')).toBeInTheDocument();
  });

  it('outline: a flat line is rejected and nothing is sent', async () => {
    const { user, frame } = await openPage(4);
    const bodies = captureSubjectBodies();
    await user.click(screen.getByRole('button', { name: 'Draw an outline' }));
    await user.type(screen.getByLabelText('What is it?'), 'stick');
    draw(frame, [[0.1, 0.1], [0.3, 0.3], [0.5, 0.5], [0.7, 0.7]]);
    expect(screen.getByRole('alert')).toHaveTextContent('too small or too flat');
    expect(screen.getByRole('button', { name: 'Save outline' })).toBeDisabled();
    expect(bodies).toHaveLength(0);
  });

  it('outline: a label is required', async () => {
    const { user, frame } = await openPage(4);
    const bodies = captureSubjectBodies();
    await user.click(screen.getByRole('button', { name: 'Draw an outline' }));
    draw(frame, circle(50));
    await user.click(screen.getByRole('button', { name: 'Save outline' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Type what the object is');
    expect(bodies).toHaveLength(0);
  });

  it('outline: Clear and redraw empties the shape', async () => {
    const { user, frame } = await openPage(4);
    await user.click(screen.getByRole('button', { name: 'Draw an outline' }));
    draw(frame, circle(50));
    await user.click(screen.getByRole('button', { name: 'Clear and redraw' }));
    expect(screen.queryByTestId('drawn-outline')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Save outline' })).toBeDisabled();
  });

  it('outline: a stroke must start on the page, and a second finger is ignored', async () => {
    const { user, frame } = await openPage(4);
    await user.click(screen.getByRole('button', { name: 'Draw an outline' }));
    draw(frame, [[-0.1, 0.5], [0.5, 0.2], [0.8, 0.8], [0.2, 0.8]].map(([x, y]) => [x, y] as NormPoint));
    expect(screen.queryByTestId('drawn-outline')).not.toBeInTheDocument();
    draw(frame, circle(50), { pointerId: 2, isPrimary: false });
    expect(screen.queryByTestId('drawn-outline')).not.toBeInTheDocument();
  });

  it('a page with no suggestions opens on the outline tool', async () => {
    await openPage(5);
    expect(screen.getByRole('button', { name: 'Draw an outline', pressed: true })).toBeInTheDocument();
  });

  it('Confirm this subject sends POST /pages/{id}/confirm', async () => {
    const { user } = await openPage(1);
    await user.click(screen.getByRole('button', { name: 'Confirm this subject' }));
    expect(await screen.findByText('Subject confirmed.')).toBeInTheDocument();
    expect(screen.getByText('Confirmed')).toBeInTheDocument();
  });

  it('a failed cut-out shows the server error and suggests the outline', async () => {
    const { user, frame } = await openPage(3);
    await user.click(screen.getByRole('button', { name: 'Click the object' }));
    fireEvent.click(frame, at([0.5, 0.5]));
    scenarios.networkErrorNext = true;
    await user.click(screen.getByRole('button', { name: 'Cut out the object here' }));
    expect(await screen.findByText(/Could not reach the server/)).toHaveTextContent('You can draw an outline instead.');
  });

  it('positions the frame over the drawn image when the image is letterboxed', async () => {
    const { frame } = await openPage(1); // page is 1600 × 1200
    const img = screen.getByRole('img', { name: /Page 1/ });
    Object.defineProperty(img, 'naturalWidth', { value: 1600 });
    Object.defineProperty(img, 'naturalHeight', { value: 900 });
    act(() => {
      fireEvent.load(img);
    });
    await waitFor(() => expect(frame).toHaveStyle({ top: '12.5%', height: '75%', left: '0%', width: '100%' }));
    expect(screen.getByText(/not the shape the server reported/)).toBeInTheDocument();
  });
});

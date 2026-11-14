import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { App } from '../App';
import { api } from '../api';

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

async function ids() {
  const books = await api.listBooks();
  const demo = books.find((b) => b.title.startsWith('Animal Homes'))!;
  const backup = books.find((b) => b.title.startsWith('The Duck'))!;
  const [maya] = await api.listProfiles();
  return { demo, backup, maya: maya! };
}

describe('every P0 route renders', () => {
  it('Library lists books', async () => {
    renderAt('/');
    expect(await screen.findByRole('heading', { name: 'Animal Homes (mock)' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'The Duck (mock backup)' })).toBeInTheDocument();
  });

  it('Subject review shows each page with its state', async () => {
    const { demo } = await ids();
    renderAt(`/books/${demo.id}/subjects`);
    expect(await screen.findByText('Page 3')).toBeInTheDocument();
    expect(screen.getByText('Needs subject')).toBeInTheDocument();
    expect(screen.getByText('Unsupported')).toBeInTheDocument();
  });

  it('Subject editor finds a page via its book', async () => {
    const { demo } = await ids();
    const p3 = demo.pages.find((p) => p.number === 3)!;
    renderAt(`/pages/${p3.id}?book=${demo.id}`);
    expect(await screen.findByRole('heading', { name: /Page 3/ })).toBeInTheDocument();
    expect(screen.getByText('hornbill')).toBeInTheDocument();
  });

  it('Subject editor works without the ?book hint', async () => {
    const { demo } = await ids();
    renderAt(`/pages/${demo.pages[0]!.id}`);
    expect(await screen.findByRole('heading', { name: /Page 1/ })).toBeInTheDocument();
  });

  it('Profiles lists the fictional demo children with look names, not numbers', async () => {
    renderAt('/profiles');
    expect(await screen.findByRole('heading', { name: 'Maya' })).toBeInTheDocument();
    expect(screen.getByText('Look: Tinted')).toBeInTheDocument();
    expect(screen.getByText('Look: Cut-out')).toBeInTheDocument();
  });

  it('Contact sheet loads for a chosen child and look', async () => {
    const { backup, maya } = await ids();
    renderAt(`/books/${backup.id}/approve?profile=${maya.id}&level=1`);
    expect(await screen.findAllByText('Approved')).toHaveLength(3);
  });

  it('Reader refuses an unapproved version and shows no image', async () => {
    const { demo, maya } = await ids();
    renderAt(`/read/${demo.id}?profile=${maya.id}&level=1`);
    expect(await screen.findByRole('alert')).toHaveTextContent('No pages are approved for this child and look yet.');
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });

  it('the gesture test page counts a two-finger tap and shows no teacher chrome', () => {
    renderAt('/gesture-test');
    expect(screen.getByRole('heading', { name: 'Reader gesture test' })).toBeInTheDocument();
    expect(screen.queryByRole('navigation', { name: 'Main' })).not.toBeInTheDocument();
    const surface = screen.getByLabelText('Gesture test surface');
    expect(surface).toHaveClass('touch-none');
    fireEvent.pointerDown(surface, { pointerId: 1, clientX: 500, clientY: 300, pointerType: 'touch' });
    fireEvent.pointerDown(surface, { pointerId: 2, clientX: 560, clientY: 300, pointerType: 'touch' });
    fireEvent.pointerUp(surface, { pointerId: 1, clientX: 500, clientY: 300, pointerType: 'touch' });
    fireEvent.pointerUp(surface, { pointerId: 2, clientX: 560, clientY: 300, pointerType: 'touch' });
    expect(screen.getByTestId('count-two-finger-tap')).toHaveTextContent('1');
    fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(screen.getByRole('list', { name: 'Gesture log' })).toHaveTextContent('key ArrowRight → next page');
  });

  it('unknown routes show not found', () => {
    renderAt('/nope');
    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeInTheDocument();
  });
});

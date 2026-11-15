/** Child profiles screen: create, edit, contrast override, and "trying colors never saves". */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http } from 'msw';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { App } from '../App';
import { api } from '../api';
import { server } from '../mocks/node';

interface Call {
  method: string;
  path: string;
  body: unknown;
}

/** Record every non-GET request, then let the mock handle it. */
function captureWrites(): Call[] {
  const calls: Call[] = [];
  server.use(
    http.all('*/api/*', async ({ request }) => {
      if (request.method !== 'GET') {
        const text = await request.clone().text();
        calls.push({ method: request.method, path: new URL(request.url).pathname, body: text ? (JSON.parse(text) as unknown) : null });
      }
      return undefined;
    }),
  );
  return calls;
}

function openProfiles() {
  render(
    <MemoryRouter initialEntries={['/profiles']}>
      <App />
    </MemoryRouter>,
  );
  return userEvent.setup();
}

const swatch = (name: string) => screen.getByRole('button', { name: new RegExp(`^${name}`) });
const writesTo = (calls: Call[], method: string, prefix: string) => calls.filter((c) => c.method === method && c.path.startsWith(prefix));

describe('Child profiles', () => {
  it('creates a profile: look by name, sent as a number, colors in order, all settings fields', async () => {
    const user = openProfiles();
    const calls = captureWrites();
    await screen.findByRole('heading', { name: 'Maya' });
    await user.click(screen.getByRole('button', { name: 'New child profile' }));

    await user.type(screen.getByLabelText('First name'), 'Ana');
    await user.click(screen.getByRole('radio', { name: /Faded page/ }));
    await user.click(swatch('Green'));
    await user.click(swatch('Red')); // remove the default
    await user.click(swatch('Blue'));
    await user.click(screen.getByRole('radio', { name: /Navy/ }));
    await user.click(screen.getByRole('button', { name: 'Save profile' }));

    expect(await screen.findByText('Ana’s profile was created.')).toBeInTheDocument();
    expect(writesTo(calls, 'POST', '/api/profiles')[0]?.body).toEqual({
      name: 'Ana',
      level: 3,
      settings: { colors: ['#43A047', '#1E88E5'], background: '#001F3F', size: 'medium', position: 'center', text_mode: 'off', outline: 'off' },
      contrast_override_note: null,
    });
    const card = within((await screen.findByRole('heading', { name: 'Ana' })).closest('li')!);
    expect(card.getByText('Look: Faded page')).toBeInTheDocument();
  });

  it('requires a name and a look, and sends nothing until they are given', async () => {
    const user = openProfiles();
    const calls = captureWrites();
    await user.click(await screen.findByRole('button', { name: 'New child profile' }));
    await user.click(screen.getByRole('button', { name: 'Save profile' }));
    expect(screen.getByText('Enter the child’s first name.')).toBeInTheDocument();
    expect(screen.getByText('Choose a look.')).toBeInTheDocument();
    expect(writesTo(calls, 'POST', '/api/profiles')).toHaveLength(0);
  });

  it('allows at most three colors, at least one, and lets the teacher pick the main one', async () => {
    const user = openProfiles();
    await user.click(await screen.findByRole('button', { name: 'New child profile' }));
    expect(swatch('Red')).toBeDisabled(); // the only color cannot be removed
    await user.click(swatch('Green'));
    await user.click(swatch('Blue'));
    expect(swatch('Yellow')).toBeDisabled();
    expect(swatch('Red')).toHaveTextContent('(main)');
    await user.click(screen.getByRole('button', { name: 'Make Blue main' }));
    expect(swatch('Blue')).toHaveTextContent('(main)');
    expect(swatch('Red')).toHaveTextContent('(2)');
  });

  it('warns below 3:1 and needs a note to keep the colors; the note is saved', async () => {
    const user = openProfiles();
    const calls = captureWrites();
    await user.click(await screen.findByRole('button', { name: 'New child profile' }));
    await user.type(screen.getByLabelText('First name'), 'Sam');
    await user.click(screen.getByRole('radio', { name: /Tinted/ }));
    await user.click(swatch('Yellow'));
    await user.click(screen.getByRole('button', { name: 'Make Yellow main' }));
    await user.click(screen.getByRole('radio', { name: /White/ }));

    expect(screen.getByText(/Yellow on white has a contrast of 1\.\d to 1, below 3 to 1/)).toBeInTheDocument();
    expect(screen.getByText(/not a clinical rule for CVI/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Save profile' }));
    expect(screen.getByText(/Write a short note to keep these colors/)).toBeInTheDocument();
    expect(writesTo(calls, 'POST', '/api/profiles')).toHaveLength(0);

    await user.type(screen.getByLabelText('To keep these colors, say why'), 'Matches the book’s yellow sun');
    await user.click(screen.getByRole('button', { name: 'Save profile' }));
    await screen.findByText('Sam’s profile was created.');
    expect((writesTo(calls, 'POST', '/api/profiles')[0]?.body as { contrast_override_note: string }).contrast_override_note).toBe(
      'Matches the book’s yellow sun',
    );
  });

  it('size and position controls are saved and previewed; the words have no control', async () => {
    const user = openProfiles();
    const calls = captureWrites();
    const [, leo] = await api.listProfiles();
    await user.click(await screen.findByRole('button', { name: 'Edit Leo' }));
    expect(screen.getByRole('radio', { name: /Medium/ })).toBeChecked();
    expect(screen.getByRole('radio', { name: 'Center' })).toBeChecked();
    // The words are always shown in one type at every look; there is no control for them.
    expect(screen.queryByRole('checkbox', { name: /words below/ })).not.toBeInTheDocument();
    expect(screen.getByText(/There is nothing to set/)).toBeInTheDocument();

    await user.click(screen.getByRole('radio', { name: /Large/ }));
    await user.click(screen.getByRole('radio', { name: 'Left' }));
    await waitFor(() => {
      const last = writesTo(calls, 'POST', '/api/preview').at(-1)?.body as { settings: Record<string, string> } | undefined;
      expect(last?.settings).toEqual(expect.objectContaining({ size: 'large', position: 'left', text_mode: leo!.settings.text_mode }));
    });
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    await screen.findByText('Leo’s profile was saved.');
    const patch = writesTo(calls, 'PATCH', `/api/profiles/${leo!.id}`)[0]?.body as { settings: Record<string, string> };
    expect(patch.settings).toEqual({ ...leo!.settings, size: 'large', position: 'left' });
    const card = within((await screen.findByRole('heading', { name: 'Leo' })).closest('li')!);
    expect(card.getByText(/Large · Left/)).toBeInTheDocument();
  });

  it('a custom colour can be added, made main, warns on low contrast, and is saved as hex', async () => {
    const user = openProfiles();
    const calls = captureWrites();
    await user.click(await screen.findByRole('button', { name: 'New child profile' }));
    await user.type(screen.getByLabelText('First name'), 'Ana');
    await user.click(screen.getByRole('radio', { name: /Cut-out/ }));
    const hex = screen.getByLabelText('Hex code');
    await user.clear(hex);
    await user.type(hex, '12ab');
    expect(screen.getByRole('button', { name: 'Add this color' })).toBeDisabled();
    await user.clear(hex);
    await user.type(hex, '#F5E6A3');
    await user.click(screen.getByRole('button', { name: 'Add this color' }));
    expect(within(screen.getByRole('list', { name: 'Custom colors chosen' })).getByText('Custom #F5E6A3')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Make Custom #F5E6A3 main' }));
    await user.click(screen.getByRole('radio', { name: /White/ }));
    expect(screen.getByText(/Custom #F5E6A3 on white has a contrast of/)).toBeInTheDocument();
    await user.type(screen.getByLabelText('To keep these colors, say why'), 'Her favourite');
    await user.click(screen.getByRole('button', { name: 'Save profile' }));
    await screen.findByText('Ana’s profile was created.');
    const body = writesTo(calls, 'POST', '/api/profiles')[0]?.body as { settings: { colors: string[] } };
    expect(body.settings.colors).toEqual(['#F5E6A3', '#E53935']);
  });

  it('editing Leo keeps his other settings and says approvals will need redoing', async () => {
    const user = openProfiles();
    const calls = captureWrites();
    const [, leo] = await api.listProfiles();
    await user.click(await screen.findByRole('button', { name: 'Edit Leo' }));
    expect(screen.getByLabelText('First name')).toHaveValue('Leo');
    expect(screen.getByRole('radio', { name: /Cut-out/ })).toBeChecked();
    expect(screen.queryByText(/need approval again/)).not.toBeInTheDocument();

    await user.click(screen.getByRole('radio', { name: /Dark gray/ }));
    expect(screen.getByText(/pages approved for Leo need approval again/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    await screen.findByText('Leo’s profile was saved.');

    const patch = writesTo(calls, 'PATCH', `/api/profiles/${leo!.id}`)[0]?.body as { settings: unknown; level: number };
    expect(patch.level).toBe(2);
    expect(patch.settings).toEqual({ ...leo!.settings, background: '#333333' });
  });

  it('trying colors and looks only previews: nothing is saved and approvals are untouched', async () => {
    const [maya] = await api.listProfiles();
    const backup = (await api.listBooks()).find((b) => b.title.startsWith('The Duck'))!;
    const user = openProfiles();
    const calls = captureWrites();
    await user.click(await screen.findByRole('button', { name: 'Edit Maya' }));
    expect(await screen.findByRole('img', { name: /Preview of The Duck/ })).toBeInTheDocument();

    await user.click(swatch('Purple'));
    await user.click(screen.getByRole('button', { name: 'Make Purple main' }));
    await user.click(screen.getByRole('radio', { name: /White/ }));
    await user.click(screen.getByRole('radio', { name: /Outlined/ }));
    await waitFor(() => {
      const last = writesTo(calls, 'POST', '/api/preview').at(-1)?.body as { level: number; settings: { background: string } } | undefined;
      expect(last?.level).toBe(4);
      expect(last?.settings.background).toBe('#FFFFFF');
    });
    await user.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(calls.filter((c) => c.path.startsWith('/api/profiles'))).toHaveLength(0);
    const after = (await api.listProfiles())[0]!;
    expect(after.settings_hash).toBe(maya!.settings_hash);
    const manifest = await api.getReaderManifest(backup.id, { profile: maya!.id, level: 1 });
    expect(manifest.pages.length).toBeGreaterThan(0);
  });

  it('the preview uses the chosen sample page and the unsaved settings', async () => {
    const user = openProfiles();
    const calls = captureWrites();
    await user.click(await screen.findByRole('button', { name: 'New child profile' }));
    expect(screen.getByText('Choose a look to see the preview.')).toBeInTheDocument();
    await user.click(screen.getByRole('radio', { name: /Cut-out/ }));
    const select = screen.getByLabelText('Sample page') as HTMLSelectElement;
    const second = select.options[1]!;
    await user.selectOptions(select, second.value);
    await waitFor(() => {
      const last = writesTo(calls, 'POST', '/api/preview').at(-1)?.body as { page_id: string; level: number } | undefined;
      expect(last).toEqual(expect.objectContaining({ page_id: second.value, level: 2 }));
    });
    expect(await screen.findByRole('img', { name: /Preview of .* in Cut-out/ })).toBeInTheDocument();
  });
});

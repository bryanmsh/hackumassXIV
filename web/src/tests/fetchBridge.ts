/**
 * Test-environment glue between jsdom and Node's fetch. Used by the mock test
 * run (setup.ts) and the live-server run (live/setup.live.ts). Never shipped.
 */
import { File as NodeFile } from 'node:buffer';

// jsdom lacks object URLs; images in tests only need a stable fake.
let urlCounter = 0;
if (!('createObjectURL' in URL)) {
  Object.assign(URL, {
    createObjectURL: () => `blob:mock/${++urlCounter}`,
    revokeObjectURL: () => undefined,
  });
}

/**
 * jsdom's AbortSignal is not the one Node's fetch accepts ("Expected signal to
 * be an instance of AbortSignal"). Bridge it: honor aborts ourselves and pass
 * the request on without the foreign signal. Uploads get the same treatment
 * for FormData (see prepare). Test environment only.
 */
let innerFetch: typeof fetch;

/** Read a jsdom Blob (which lacks arrayBuffer()) into Node bytes. */
function readBlob(blob: Blob): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(Buffer.from(reader.result as ArrayBuffer));
    reader.onerror = () => reject(reader.error);
    reader.readAsArrayBuffer(blob);
  });
}

/**
 * jsdom's FormData is not something Node's fetch can send, so uploads would
 * arrive empty. Encode it as a real multipart body, the way a browser does.
 */
async function encodeMultipart(form: FormData): Promise<{ body: Buffer; contentType: string }> {
  const boundary = `----mirai-test-${Math.random().toString(16).slice(2)}`;
  const parts: Buffer[] = [];
  for (const [name, value] of form.entries()) {
    if (typeof value === 'string') {
      parts.push(Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="${name}"\r\n\r\n${value}\r\n`));
    } else {
      const file = value as File;
      parts.push(
        Buffer.from(
          `--${boundary}\r\nContent-Disposition: form-data; name="${name}"; filename="${file.name}"\r\n` +
            `Content-Type: ${file.type || 'application/octet-stream'}\r\n\r\n`,
        ),
      );
      parts.push(await readBlob(file), Buffer.from('\r\n'));
    }
  }
  parts.push(Buffer.from(`--${boundary}--\r\n`));
  return { body: Buffer.concat(parts), contentType: `multipart/form-data; boundary=${boundary}` };
}

async function prepare(init: RequestInit): Promise<RequestInit> {
  if (!(init.body instanceof FormData)) return init;
  const { body, contentType } = await encodeMultipart(init.body);
  // Node's fetch takes a Buffer; the DOM typings only know browser body types.
  return { ...init, body: body as unknown as BodyInit, headers: { ...(init.headers as Record<string, string>), 'Content-Type': contentType } };
}

/**
 * Node's multipart parser builds files with the global File, which jsdom
 * replaces, and then rejects them. Let mock handlers parse uploads by using
 * Node's File for the duration of request.formData(). Test environment only.
 */
function bridgeFormDataParsing() {
  const original = Request.prototype.formData;
  Request.prototype.formData = async function formData(this: Request) {
    const g = globalThis as { File: unknown };
    const jsdomFile = g.File;
    g.File = NodeFile;
    try {
      return await original.call(this);
    } finally {
      g.File = jsdomFile;
    }
  };
}

function bridgeFetch() {
  innerFetch = globalThis.fetch;
  globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const signal = init?.signal;
    const { signal: _foreign, ...rest } = init ?? {};
    const abortError = () => new DOMException('The operation was aborted.', 'AbortError');
    if (signal?.aborted) throw abortError();
    const ready = await prepare(rest);
    if (!signal) return innerFetch(input, ready);
    if (signal.aborted) throw abortError();
    return new Promise<Response>((resolve, reject) => {
      const onAbort = () => reject(abortError());
      signal.addEventListener('abort', onAbort, { once: true });
      innerFetch(input, ready).then(resolve, reject).finally(() => signal.removeEventListener('abort', onAbort));
    });
  };
}

/** Install every shim. Call after MSW's server.listen() so MSW's fetch is wrapped. */
export function installTestBridges(): void {
  bridgeFetch();
  bridgeFormDataParsing();
}

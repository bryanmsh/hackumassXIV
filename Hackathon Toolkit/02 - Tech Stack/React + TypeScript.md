# React + TypeScript

Docs: https://react.dev/ and https://vite.dev/guide/
```bash
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install && npm run dev
```
Minimal API call:
```tsx
import { useState } from 'react';
export default function App() {
  const [text, setText] = useState('');
  const [result, setResult] = useState('');
  async function run() {
    try {
      const r = await fetch('http://localhost:8000/analyze', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({text})
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setResult(JSON.stringify(await r.json()));
    } catch (e) { setResult(String(e)); }
  }
  return <main><input value={text} onChange={e=>setText(e.target.value)}/><button onClick={run}>Run</button><pre>{result}</pre></main>;
}
```
Avoid exposing API keys in Vite client environment variables. Use backend proxy for secrets. See [[Integration Checklist]].

// Run with `--root web`, so the include path is relative to web/. A plain object (no `vitest/config`
// import) because this file lives outside web/, where that package cannot be resolved.
// No setup files: Thomas's mock server must not start.
export default {
  test: {
    environment: 'node',
    globals: true,
    include: ['../api/joining/*.test.ts'],
    testTimeout: 60_000,
  },
};

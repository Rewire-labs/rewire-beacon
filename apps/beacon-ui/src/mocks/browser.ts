// Browser-side MSW worker bootstrap for beacon-ui.
//
// Usage in src/main.tsx:
//
//   if (import.meta.env.DEV && import.meta.env.VITE_MSW === 'true') {
//     const { worker } = await import('./mocks/browser');
//     await worker.start();
//   }

import { setupWorker } from 'msw/browser';

import { handlers } from './handlers';

export const worker = setupWorker(...handlers);

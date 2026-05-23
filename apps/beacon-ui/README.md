# beacon-ui

BEACON Notification Platform — UI multi-canal BR (email, SMS, WhatsApp, push) com audit chain BLAKE3, deliverability ML e compliance LGPD.

## Stack

- Vite + React 19 + TypeScript
- Tailwind 3 + shadcn-style primitives (`@/components/beacon/ui`)
- React Router 7 (montado em `/app/produtos/beacon/*`)
- lucide-react para icones
- Mock data em `@/content/beacon-mock` (V0; sera substituido por beacon-control-plane)

## Dev

```bash
npm install
npm run dev    # http://localhost:5177
```

Build:

```bash
npm run build
npm run preview
```

## Estrutura

- `src/pages/beacon/` — 19 telas (Overview, Messages, Templates, Journeys, etc.)
- `src/components/beacon/` — Shell + Sidebar + Topbar + `ui.tsx` (primitives)
- `src/content/beacon-mock.ts` — fixtures V0
- `src/App.tsx` — rotas

## Docker

```bash
docker build -f apps/beacon-ui/Dockerfile -t beacon-ui:dev .
docker run -p 8080:8080 beacon-ui:dev
```

Em producao, nginx serve `dist/` em `:8080` e proxia `/api/*` para `installer-backend-proxy.installer.svc`.

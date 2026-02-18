# Beacon Frontend

React + TypeScript UI for Beacon.

## Run

From repo root:

```bash
make install
make dev-frontend
```

Or from `frontend/`:

```bash
npm install
npm run dev
```

Frontend runs on `http://localhost:5173` and proxies:
- `/v1` -> backend `http://localhost:7474`
- `/ws` -> backend websocket `ws://localhost:7474`

## Scripts

```bash
npm run dev
npm run build
npm run lint
npm run typecheck
npm run preview
```

## Key Source Files

- `src/App.tsx` - root layout + route definitions
- `src/pages/` - Dashboard, Traces, Playground, Settings
- `src/store/` - Zustand stores
- `src/lib/api.ts` - REST client
- `src/lib/ws.ts` - WebSocket client
- `src/components/` - feature components
- `src/index.css` - theme tokens/styles

## Notes

- Do not edit `src/components/ui/` unless intentionally modifying shared shadcn primitives.
- API contracts are documented in `../docs/api-contracts.md`.

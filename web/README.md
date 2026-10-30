# SAIRA frontend

React + Vite + Tailwind v4, with [Animate UI](https://animate-ui.com) primitives
over Radix for the motion. Builds to `../static/build`, which FastAPI serves
from its `/static` mount; every page route returns the same shell and
react-router picks the page.

Node 22 is required (Vite 8 refuses anything older):

```bash
nvm use 22
cd web
npm install
npm run build        # -> ../static/build, committed so the server needs no Node
npm run dev          # localhost:5173, proxies /api and /ws to :3001
```

For `npm run dev`, start the Python server on port 3001 first — the Vite proxy
forwards the API calls and the voice WebSocket to it.

## Layout

| Path | Holds |
| --- | --- |
| `src/pages/` | One file per route: landing, login, register, assistant, admin |
| `src/components/site/` | Marketing chrome and the landing page's sections |
| `src/components/ui/` | shadcn components, with their primitives swapped for Animate UI's |
| `src/components/animate-ui/` | Registry components pulled in whole, e.g. the stars background |
| `src/hooks/use-voice-session.ts` | The microphone, the `/ws/voice` socket and audio playback |
| `src/lib/api.ts` | Typed wrappers over the routes in `core/routes.py` |

## Animate UI

`npx @animate-ui/cli@latest animate all` rewrites the shadcn components in
`src/components/ui/` to import their primitives from `@animate-ui/react`
instead of `radix-ui`, and strips the CSS animations Motion replaces. Re-run it
after adding a shadcn component. Pace is set once, in `src/App.tsx`, through
`AnimateUIProvider tempo`.

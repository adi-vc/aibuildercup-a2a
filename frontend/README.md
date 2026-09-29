# Vachan — Frontend (Player)

React + Vite + TypeScript player. Fetches a manifest from the API and composes the video in the browser — no generation, only composition.

## Requirements

- Node 20+
- The backend API running at `http://localhost:8080` (or `VITE_API_BASE_URL` set)

## Local dev

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

The Vite dev server proxies `/v1/…` to `http://localhost:8080` automatically (see `vite.config.ts`), so no CORS issues locally.

The player loads the `p0_single_beat` manifest by default. Pass `?manifest=<id>` to load a different fixture.

## Build

```bash
npm run build    # outputs to dist/
npm run preview  # preview the production build locally
```

## Type check

```bash
npx tsc --noEmit
```

## Structure

```
frontend/
  src/
    types/
      manifest.ts         TypeScript types mirroring the manifest schema (§28)
    api/
      client.ts           fetchManifest(), ingestUrl()
    hooks/
      useManifest.ts      React hook — loads a manifest by id
    components/
      BeatPlayer.tsx      P0 single-beat player: plate + text layer + locale select + badges
      BeatPlayer.module.css
    App.tsx               Root; reads ?manifest= query param
    App.css
  public/
    assets/
      placeholder_flood_street.svg   P0 placeholder plate
  firebase.json     Firebase Hosting config (SPA rewrite, asset cache headers)
  .firebaserc       Set YOUR_FIREBASE_PROJECT_ID before deploying
  vite.config.ts    Dev proxy + build config
```

## Deployment

```bash
# Set your Firebase project id in .firebaserc first
npm run build
npx firebase deploy --only hosting
```

Cloud Build (`cloudbuild.yaml` in repo root) runs this automatically on push to main.

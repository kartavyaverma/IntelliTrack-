# IntelliTrack Dashboard

React (Vite) frontend for the IntelliTrack API. Four tabs:

- **Alerts** — sightings that cleared the confidence floor and cooldown (refreshes every 5 s)
- **Sightings** — every raw match event, filterable by type and camera (refreshes every 5 s)
- **Heatmaps** — the per-camera heatmap snapshot saved at the end of a Phase 6 run
- **People** — register a missing-person reference photo and browse registered people

## Run

Start the API from the repository root first:

```bash
uvicorn src.api.main:app --reload
```

Then, in this folder:

```bash
npm install
npm run dev
```

Open http://localhost:5173. The API address is set in `src/api.js`
(`http://127.0.0.1:8000`). The dev server is pinned to port 5173 because
that is the only frontend origin the API's CORS settings allow.

Other scripts: `npm run build` (production build to `dist/`), `npm run lint` (oxlint).

# Daily News Digest Web

Next.js frontend preview for the Daily News Digest project.

## Run locally

```powershell
npm install
npm run dev
```

Open `http://localhost:3000`.

## Verify

```powershell
npm run lint
npm run typecheck
npm run build
```

The current UI uses mock data from `src/data/mock-data.ts`. It does not modify
the Python pipeline, SQLite database, email sender, or GitHub Actions workflow.

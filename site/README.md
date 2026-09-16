# Gazette landing page

Next.js · TypeScript · Tailwind CSS v4.

## Dev

```bash
cd site
npm install
npm run dev
```

Open http://localhost:3000

## Structure

- `src/app/` — routes and layout
- `src/components/lpa/` — landing sections (your components go here)
- `src/lib/site.ts` — copy, links, edition faces
- `public/editions/` — Planet / Times / Herald previews

## Deploy

Vercel or GitHub Pages (static export if needed). Root of agent repo stays Docker/Hermes; this folder is only the marketing site.

# Page Dependency Trees

## `/` — Data Quality Demo

Entry: `frontend/src/main.tsx`

Dependencies:
- `frontend/src/main.tsx`
  - `frontend/src/App.tsx`
    - `frontend/src/api/client.ts`
      - `frontend/src/types/index.ts`

There are no local UI component imports yet. Phase 6 will add source input, report, diff, and answer-comparison components under `frontend/src/components/`.

# Theme

## Compact token summary

- No established product design system, CSS variables, or theme configuration exists yet.
- Current browser defaults are mostly in use; `App.tsx` sets only `font-family: system-ui, sans-serif` and `padding: 24px` inline.
- No color palette, type scale, spacing scale, radius, shadow, or breakpoint tokens are defined.
- Phase 6 design is free to establish the first coherent visual system for a professional data-quality workspace.

## Source configuration

### `frontend/vite.config.ts`

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

No `globals.css`, `index.css`, Tailwind config, CSS modules, or theme provider is present.

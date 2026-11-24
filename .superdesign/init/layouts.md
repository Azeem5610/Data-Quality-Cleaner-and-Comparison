# Layout Components

## `frontend/src/App.tsx`

Current application shell and only rendered page. It is a health-check placeholder.

```tsx
import { useEffect, useState } from "react";
import { getHealth } from "./api/client";

export default function App() {
  const [status, setStatus] = useState("checking...");

  useEffect(() => {
    getHealth()
      .then((d) => setStatus(d.status))
      .catch(() => setStatus("backend unreachable"));
  }, []);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: 24 }}>
      <h1>Data Quality Demo</h1>
      <p>Backend status: {status}</p>
    </main>
  );
}
```

## `frontend/src/main.tsx`

Application entry point; mounts `App` in React Strict Mode.

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

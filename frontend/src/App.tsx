import { useEffect, useState } from "react";

import { health } from "./api";

export default function App() {
  const [backendUp, setBackendUp] = useState<boolean | null>(null);

  useEffect(() => {
    health().then(setBackendUp);
  }, []);

  return (
    <main>
      <h1>Jev Classifier</h1>
      <p data-testid="backend-status">
        Backend:{" "}
        {backendUp === null ? "checking…" : backendUp ? "connected" : "not reachable"}
      </p>
    </main>
  );
}

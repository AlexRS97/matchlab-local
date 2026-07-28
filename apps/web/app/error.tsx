"use client";

import { useEffect } from "react";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("MatchLab render error", error);
  }, [error]);

  return (
    <main className="shell state-shell">
      <div className="state-illustration error-mark" aria-hidden="true">!</div>
      <p className="eyebrow">ALGO NO HA RESPONDIDO</p>
      <h1>No hemos podido cargar esta vista.</h1>
      <p>Los servicios y tus datos siguen intactos. Puedes reintentar o volver a la jornada.</p>
      <div className="state-actions">
        <button onClick={reset}>Reintentar</button>
        <a href="/">Volver al inicio</a>
      </div>
      {error.digest && <small>Referencia técnica: {error.digest}</small>}
    </main>
  );
}

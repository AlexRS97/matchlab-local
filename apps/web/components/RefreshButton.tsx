"use client";

import { useState } from "react";

const publicApi = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function RefreshButton({ date }: { date: string }) {
  const [state, setState] = useState<"idle" | "loading" | "done" | "error">("idle");

  async function refresh() {
    setState("loading");
    try {
      const response = await fetch(
        `${publicApi}/api/v1/admin/ingestion/run?date=${encodeURIComponent(date)}`,
        { method: "POST" },
      );
      if (!response.ok) throw new Error("No se pudo iniciar");
      setState("done");
      window.setTimeout(() => window.location.reload(), 3500);
    } catch {
      setState("error");
    }
  }

  const labels = {
    idle: "Actualizar datos",
    loading: "Iniciando…",
    done: "Actualizando…",
    error: "Reintentar",
  };
  return (
    <button className="refresh-button" onClick={refresh} disabled={state === "loading" || state === "done"}>
      <span className={state === "loading" || state === "done" ? "spin" : ""}>↻</span>
      {labels[state]}
    </button>
  );
}


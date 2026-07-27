"use client";

import { useState } from "react";

const publicApi = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Job = {
  target_date: string;
  status: "running" | "completed" | "failed";
  started_at: string | null;
};

const wait = (milliseconds: number) =>
  new Promise((resolve) => window.setTimeout(resolve, milliseconds));

export function RefreshButton({ date }: { date: string }) {
  const [state, setState] = useState<"idle" | "loading" | "done" | "error">("idle");

  async function refresh() {
    setState("loading");
    const requestedAt = Date.now();
    try {
      const response = await fetch(
        `${publicApi}/api/v1/admin/ingestion/run?date=${encodeURIComponent(date)}`,
        { method: "POST" },
      );
      if (!response.ok) throw new Error("No se pudo iniciar");

      for (let attempt = 0; attempt < 120; attempt += 1) {
        await wait(5_000);
        const jobsResponse = await fetch(`${publicApi}/api/v1/admin/jobs`, {
          cache: "no-store",
        });
        if (!jobsResponse.ok) continue;
        const jobs = await jobsResponse.json() as Job[];
        const job = jobs.find(
          (item) =>
            item.target_date === date &&
            item.started_at &&
            Date.parse(item.started_at) >= requestedAt - 5_000,
        );
        if (job?.status === "failed") throw new Error("La actualización ha fallado");
        if (job?.status === "completed") {
          setState("done");
          await wait(800);
          window.location.reload();
          return;
        }
      }
      setState("done");
      window.location.reload();
    } catch {
      setState("error");
    }
  }

  const labels = {
    idle: "Actualizar datos",
    loading: "Actualizando datos…",
    done: "Actualización completada",
    error: "Reintentar",
  };
  return (
    <button
      className="refresh-button"
      onClick={refresh}
      disabled={state === "loading" || state === "done"}
    >
      <span className={state === "loading" ? "spin" : ""}>↻</span>
      {labels[state]}
    </button>
  );
}

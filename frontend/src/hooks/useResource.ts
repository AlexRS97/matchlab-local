import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
export function useResource<T>(path: string, interval = 0) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState(0);
  const reload = useCallback(() => setVersion((v) => v + 1), []);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setData(undefined);
    let pending = false;
    async function load() {
      if (pending || controller.signal.aborted || document.hidden) return;
      pending = true;
      try {
        const result = await api<T>(path, { signal: controller.signal });
        if (!controller.signal.aborted) {
          setData(result);
          setError("");
        }
      } catch (e) {
        if (!controller.signal.aborted)
          setError(e instanceof Error ? e.message : "Error de conexión");
      } finally {
        pending = false;
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    const timer = interval ? window.setInterval(load, interval) : undefined;
    const visible = () => {
      if (!document.hidden) void load();
    };
    document.addEventListener("visibilitychange", visible);
    return () => {
      controller.abort();
      if (timer) window.clearInterval(timer);
      document.removeEventListener("visibilitychange", visible);
    };
  }, [path, interval, version]);
  return { data, error, loading, reload };
}

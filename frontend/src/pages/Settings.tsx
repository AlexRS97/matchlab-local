import { useEffect, useState } from "react";
import { Save, Server } from "lucide-react";
import { api } from "../api/client";
import { useResource } from "../hooks/useResource";
import {
  BOOKMAKERS,
  MARKETS,
  type ProvidersData,
  type UserSettings,
} from "../types";
import { ago, marketName } from "../utils/format";
import { ErrorMessage, Loading } from "../components/Primitives";

export function Settings() {
  const settings = useResource<UserSettings>("/settings");
  const providers = useResource<ProvidersData>("/providers/status", 15000);
  const [form, setForm] = useState<UserSettings>();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    if (settings.data) setForm(settings.data);
  }, [settings.data]);
  if (!form)
    return (
      <>
        <ErrorMessage message={settings.error} />
        <Loading />
      </>
    );
  function change<K extends keyof UserSettings>(
    key: K,
    value: UserSettings[K],
  ) {
    setForm((f) => (f ? { ...f, [key]: value } : f));
    setMessage("");
  }
  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await api("/settings", { method: "PUT", body: JSON.stringify(form) });
      setMessage("Preferencias guardadas.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo guardar");
    } finally {
      setSaving(false);
    }
  }
  return (
    <>
      <header className="page-header">
        <div>
          <div className="eyebrow">WORKSPACE / CONFIGURACIÓN</div>
          <h1>
            Settings<span>.</span>
          </h1>
          <p>Fuentes, cobertura y reglas del análisis.</p>
        </div>
      </header>
      <ErrorMessage message={error || settings.error || providers.error} />
      <div className="provider-grid">
        {providers.data?.providers.map((p) => (
          <section className="panel provider-card" key={p.provider}>
            <div>
              <Server size={15} />
              <h3>{p.provider.toUpperCase()}</h3>
              <span className="provider-state">
                {p.status.replaceAll("_", " ")}
              </span>
            </div>
            <dl className="stat-list">
              <div>
                <dt>Peticiones hoy</dt>
                <dd>{p.requests_today}</dd>
              </div>
              {p.effective_interval_minutes && (
                <div>
                  <dt>Intervalo según presupuesto</dt>
                  <dd>{p.effective_interval_minutes} min</dd>
                </div>
              )}
              <div>
                <dt>Disponibles / {p.period === "month" ? "mes" : "día"}</dt>
                <dd>{p.requests_remaining}</dd>
              </div>
              <div>
                <dt>Última conexión correcta</dt>
                <dd>{ago(p.last_success)}</dd>
              </div>
              <div>
                <dt>Reinicio de cuota</dt>
                <dd>{new Date(p.reset_time).toLocaleString("es-ES")}</dd>
              </div>
            </dl>
            {p.last_error && <p className="provider-error">{p.last_error}</p>}
            {p.warnings?.map((w) => (
              <p className="provider-error" key={w}>
                {w}
              </p>
            ))}
            {!p.configured && (
              <p className="subtle">
                Configura sus credenciales en backend/.env y reinicia el
                backend.
              </p>
            )}
          </section>
        ))}
      </div>
      <div className="book-availability">
        {providers.data?.bookmakers.map((b) => (
          <span key={b.bookmaker}>
            <b>{b.bookmaker}</b>
            {b.available_prices} partidos con cuotas recientes
          </span>
        ))}
      </div>
      <form onSubmit={save} className="settings-form">
        <div className="two-columns">
          <section className="panel">
            <h2>Selección de partidos</h2>
            <div className="settings-grid">
              <label>
                Casa por defecto
                <select
                  value={form.default_bookmaker}
                  onChange={(e) =>
                    change(
                      "default_bookmaker",
                      e.target.value as UserSettings["default_bookmaker"],
                    )
                  }
                >
                  <option value="ALL">Mejor cuota</option>
                  {BOOKMAKERS.map((b) => (
                    <option key={b}>{b}</option>
                  ))}
                </select>
              </label>
              <label>
                Cuota mínima
                <input
                  type="number"
                  min="1.01"
                  max="1000"
                  step=".01"
                  value={form.minimum_odds}
                  onChange={(e) =>
                    change("minimum_odds", Number(e.target.value))
                  }
                />
              </label>
              <label>
                Tamaño del Top
                <select
                  value={form.top_n}
                  onChange={(e) => change("top_n", Number(e.target.value))}
                >
                  {[5, 10, 20, 0].map((n) => (
                    <option key={n} value={n}>
                      {n || "Todos"}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Confianza mínima
                <select
                  value={form.minimum_confidence}
                  onChange={(e) => change("minimum_confidence", e.target.value)}
                >
                  {["INSUFFICIENT", "LOW", "MEDIUM", "HIGH", "VERY_HIGH"].map(
                    (v) => (
                      <option key={v}>{v}</option>
                    ),
                  )}
                </select>
              </label>
              <label>
                Calidad mínima
                <select
                  value={form.minimum_data_quality}
                  onChange={(e) =>
                    change("minimum_data_quality", e.target.value)
                  }
                >
                  {[
                    "INSUFFICIENT",
                    "LOW",
                    "ACCEPTABLE",
                    "GOOD",
                    "EXCELLENT",
                  ].map((v) => (
                    <option key={v}>{v}</option>
                  ))}
                </select>
              </label>
            </div>
            <label className="spaced-label">
              Países (separados por comas; vacío = todos)
              <input
                value={form.enabled_countries.join(", ")}
                onChange={(e) =>
                  change(
                    "enabled_countries",
                    e.target.value.split(",").map((v) => v.trim()),
                  )
                }
                onBlur={() =>
                  change(
                    "enabled_countries",
                    form.enabled_countries.filter(Boolean),
                  )
                }
              />
            </label>
            <label className="spaced-label">
              IDs de ligas (separados por comas; vacío = todas)
              <input
                defaultValue={form.enabled_leagues.join(", ")}
                onBlur={(e) =>
                  change(
                    "enabled_leagues",
                    e.target.value
                      .split(",")
                      .map((v) => Number(v.trim()))
                      .filter((n) => Number.isInteger(n) && n > 0),
                  )
                }
              />
            </label>
          </section>
          <section className="panel">
            <h2>Actualización y antigüedad</h2>
            <div className="settings-grid">
              {(
                [
                  ["fixtures_minutes", "Partidos", 15],
                  ["standings_minutes", "Clasificación", 180],
                  ["stats_minutes", "Estadísticas", 60],
                  ["betfair_minutes", "Betfair", 5],
                  ["pulsescore_minutes", "PulseScore", 5],
                  ["odds_stale_minutes", "Cuota obsoleta a partir de", 5],
                ] as const
              ).map(([key, label, min]) => (
                <label key={key}>
                  {label} (min)
                  <input
                    type="number"
                    required
                    min={min}
                    max="1440"
                    value={form[key]}
                    onChange={(e) => change(key, Number(e.target.value))}
                  />
                </label>
              ))}
            </div>
            <p className="subtle">
              El refresco respeta la caché y el presupuesto de cada API.
              PulseScore adapta el intervalo al saldo mensual; una cuota antigua
              se excluye del Top.
            </p>
            <div className="settings-checks spaced-label">
              {BOOKMAKERS.map((b) => (
                <label className="settings-check" key={b}>
                  <input
                    type="checkbox"
                    checked={form.enabled_bookmakers.includes(b)}
                    onChange={(e) =>
                      change(
                        "enabled_bookmakers",
                        e.target.checked
                          ? [...form.enabled_bookmakers, b]
                          : form.enabled_bookmakers.filter((v) => v !== b),
                      )
                    }
                  />
                  {b}
                </label>
              ))}
              <label className="settings-check">
                <input
                  type="checkbox"
                  checked={form.betfair_fallback}
                  onChange={(e) => change("betfair_fallback", e.target.checked)}
                />
                Permitir Orbit Exchange vía PulseScore como alternativa de
                Betfair
              </label>
            </div>
            <p className="subtle">
              Orbit conserva su etiqueta de origen. Las credenciales solo se
              leen en el servidor.
            </p>
          </section>
        </div>
        <section className="panel detail-section">
          <h2>Mercados habilitados</h2>
          <div className="market-checks">
            {MARKETS.map((m) => (
              <label className="settings-check" key={m}>
                <input
                  type="checkbox"
                  checked={form.enabled_markets.includes(m)}
                  onChange={(e) =>
                    change(
                      "enabled_markets",
                      e.target.checked
                        ? [...form.enabled_markets, m]
                        : form.enabled_markets.filter((v) => v !== m),
                    )
                  }
                />
                {marketName(m)}
              </label>
            ))}
          </div>
        </section>
        <div className="save-row">
          <button className="primary-button" disabled={saving}>
            <Save size={15} />
            {saving ? "Guardando…" : "Guardar preferencias"}
          </button>
          <p role="status">{message}</p>
        </div>
      </form>
    </>
  );
}

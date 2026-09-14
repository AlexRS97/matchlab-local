import { useEffect, useMemo, useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  SlidersHorizontal,
  RefreshCw,
  Search,
} from "lucide-react";
import { api } from "../api/client";
import { useResource } from "../hooks/useResource";
import {
  BOOKMAKERS,
  MARKETS,
  type Pick,
  type TodayData,
  type UserSettings,
} from "../types";
import { ago, localDate, marketName, normalize } from "../utils/format";
import { FixturesTable } from "../components/FixturesTable";
import { PickCard } from "../components/PickCard";
import { Empty, ErrorMessage, Loading } from "../components/Primitives";
import { ManualOdds } from "../components/ManualOdds";

export function Today() {
  const [params, setParams] = useSearchParams();
  const location = useLocation();
  const date = params.get("date") ?? localDate();
  const section = location.pathname;
  const corners = section === "/corners";
  const [market, setMarket] = useState("OVER_2_5_GOALS");
  const [bookmaker, setBookmaker] = useState("ALL");
  const [minOdds, setMinOdds] = useState("1.35");
  const [maxOdds, setMaxOdds] = useState("");
  const [topN, setTopN] = useState("5");
  const [country, setCountry] = useState("");
  const [league, setLeague] = useState("");
  const [notStarted, setNotStarted] = useState(false);
  const [minProb, setMinProb] = useState("");
  const [minEdge, setMinEdge] = useState("");
  const [minEv, setMinEv] = useState("");
  const [minConfidence, setMinConfidence] = useState("");
  const [minQuality, setMinQuality] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [applyOdds, setApplyOdds] = useState(false);
  const [message, setMessage] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const search = params.get("search") ?? "";
  const { data, error, loading, reload } = useResource<TodayData>(
    `/today?date=${date}`,
    15000,
  );
  const { data: settings } = useResource<UserSettings>("/settings");
  useEffect(() => {
    if (settings) {
      setMinOdds(String(settings.minimum_odds));
      setBookmaker(settings.default_bookmaker);
      setTopN(String(settings.top_n));
    }
  }, [settings]);
  useEffect(() => {
    setMarket(corners ? "OVER_9_5_CORNERS" : "OVER_2_5_GOALS");
  }, [corners]);
  const topQuery = new URLSearchParams({
    date,
    market,
    bookmaker: bookmaker.toLowerCase(),
    min_odds: minOdds || "1.35",
    top_n: topN,
  });
  for (const [key, value] of Object.entries({
    max_odds: maxOdds,
    min_probability: minProb ? String(Number(minProb) / 100) : "",
    min_edge: minEdge ? String(Number(minEdge) / 100) : "",
    min_ev: minEv ? String(Number(minEv) / 100) : "",
    country,
    league_id: league,
    search,
    kickoff_from: from,
    kickoff_to: to,
    min_confidence: minConfidence,
    min_quality: minQuality,
  }))
    if (value) topQuery.set(key, value);
  const {
    data: picks,
    error: topError,
    reload: reloadTop,
  } = useResource<Pick[]>(`/top?${topQuery}`, 15000);
  function setDate(value: string) {
    const next = new URLSearchParams(params);
    next.set("date", value);
    setParams(next);
  }
  function shiftDate(delta: number) {
    const d = new Date(`${date}T12:00:00Z`);
    d.setUTCDate(d.getUTCDate() + delta);
    setDate(d.toISOString().slice(0, 10));
  }
  const filtered = useMemo(
    () =>
      (data?.fixtures ?? []).filter((f) => {
        const m = f.markets[market];
        const p = m?.model_probability;
        const q =
          bookmaker === "ALL"
            ? m?.best
            : m?.quotes[bookmaker as keyof typeof m.quotes];
        const names = [f.home_team, f.away_team, ...(f.search_names ?? [])]
          .map(normalize)
          .join(" ");
        if (search && !names.includes(normalize(search))) return false;
        if (
          (country && f.country !== country) ||
          (league && f.league_id !== Number(league))
        )
          return false;
        if (
          notStarted &&
          (f.status !== "NOT_STARTED" ||
            new Date(f.kickoff_utc).getTime() <= Date.now())
        )
          return false;
        const kickoff = (f.kickoff_local ?? "").slice(11, 16);
        if ((from && kickoff < from) || (to && kickoff > to)) return false;
        if (minProb && (p == null || p < Number(minProb) / 100)) return false;
        if (minEdge && (q?.edge == null || q.edge < Number(minEdge) / 100))
          return false;
        if (minEv && (q?.ev == null || q.ev < Number(minEv) / 100))
          return false;
        const confidence = f.prediction?.confidence[market]?.score ?? 0;
        const quality =
          (market.endsWith("CORNERS")
            ? f.prediction?.corner_quality
            : f.prediction?.quality
          )?.score ?? 0;
        if (
          minConfidence &&
          confidence <
            ({ LOW: 40, MEDIUM: 60, HIGH: 75, VERY_HIGH: 90 }[minConfidence] ??
              0)
        )
          return false;
        if (
          minQuality &&
          quality <
            ({ LOW: 40, ACCEPTABLE: 60, GOOD: 75, EXCELLENT: 90 }[minQuality] ??
              0)
        )
          return false;
        if (
          applyOdds &&
          (!q ||
            q.stale ||
            q.decimal_odds < Number(minOdds) ||
            (maxOdds && q.decimal_odds > Number(maxOdds)))
        )
          return false;
        return true;
      }),
    [
      data,
      market,
      bookmaker,
      country,
      league,
      search,
      notStarted,
      minProb,
      minEdge,
      minEv,
      minConfidence,
      minQuality,
      from,
      to,
      applyOdds,
      minOdds,
      maxOdds,
    ],
  );
  async function refresh() {
    setRefreshing(true);
    setMessage("");
    try {
      await api(
        date === localDate() ? "/refresh/daily" : `/refresh?date=${date}`,
        { method: "POST" },
      );
      reload();
      reloadTop();
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setRefreshing(false);
    }
  }
  const title =
    section === "/top"
      ? "Top Picks"
      : section === "/goals"
        ? "Goles"
        : corners
          ? "Córners"
          : section === "/odds"
            ? "Comparador de cuotas"
            : date === localDate()
              ? "Hoy"
              : "La jornada";
  return (
    <>
      <header className="page-header">
        <div>
          <div className="eyebrow">
            FOOTBALL INTELLIGENCE <span> / </span> PREPARTIDO
          </div>
          <h1>
            {title}
            <span className="title-dot">.</span>
          </h1>
          <p>Toda la jornada. Datos, modelos y precios en una sola vista.</p>
        </div>
        <div className="header-actions">
          <div className="date-picker">
            <button aria-label="Día anterior" onClick={() => shiftDate(-1)}>
              <ArrowLeft size={15} />
            </button>
            <input
              aria-label="Fecha de la jornada"
              type="date"
              value={date}
              onChange={(e) => e.target.value && setDate(e.target.value)}
            />
            <button aria-label="Día siguiente" onClick={() => shiftDate(1)}>
              <ArrowRight size={15} />
            </button>
          </div>
          <button
            className="primary-button"
            onClick={refresh}
            disabled={refreshing || data?.job.running}
          >
            <RefreshCw size={15} className={data?.job.running ? "spin" : ""} />
            {data?.job.running ? "Actualizando" : "Actualizar"}
          </button>
        </div>
      </header>
      <ErrorMessage message={error || message} />
      {data?.job.errors.length ? (
        <div className="notice warning">
          <b>Cobertura parcial</b>
          <span>{data.job.errors.join(" · ")}</span>
        </div>
      ) : null}
      {data && (
        <>
          <div className="stats-grid">
            {[
              ["Partidos disponibles", data.fixtures_found],
              ["Analizados", data.fixtures_analysed],
              ["Datos completos", data.complete_data],
              ["Datos parciales", data.partial_data],
              ["Sin datos suficientes", data.insufficient_data],
            ].map(([label, value], i) => (
              <div className="stat-card" key={label}>
                <span>{label}</span>
                <strong className={i === 1 ? "positive" : ""}>{value}</strong>
                <small>
                  {
                    [
                      "Toda la cobertura del proveedor",
                      "Modelos de goles disponibles",
                      "Calidad GOOD o EXCELLENT",
                      "Análisis con cobertura limitada",
                      "Se mantienen en la cartelera",
                    ][i]
                  }
                </small>
              </div>
            ))}
          </div>
          <div className="freshness">
            <span>
              <i />
              ESTADÍSTICAS · {ago(data.last_stats_update)}
            </span>
            <span>CUOTAS · {ago(data.last_odds_update)}</span>
            {data.daily_analysis && (
              <span
                title={`Siguiente ciclo: ${new Date(data.daily_analysis.next_scheduled_at).toLocaleString("es-ES")}`}
              >
                ANÁLISIS DIARIO ·{" "}
                {data.daily_analysis.last?.date === localDate()
                  ? `${data.daily_analysis.last.status === "complete" ? "completado" : data.daily_analysis.last.status === "partial" ? "parcial" : "sin datos"} ${ago(data.daily_analysis.last.finished_at)}`
                  : `pendiente · ${String(data.daily_analysis.hour).padStart(2, "0")}:00`}
              </span>
            )}
            <span>{data.timezone}</span>
          </div>
        </>
      )}
      <section className="filters">
        <div className="filter-main">
          <label className="search-field">
            <Search size={16} />
            <input
              aria-label="Buscar equipo"
              placeholder="Buscar equipo o alias…"
              value={search}
              onChange={(e) => {
                const next = new URLSearchParams(params);
                next.set("search", e.target.value);
                setParams(next, { replace: true });
              }}
            />
          </label>
          <label>
            Mercado
            <select value={market} onChange={(e) => setMarket(e.target.value)}>
              {MARKETS.filter((m) =>
                section === "/goals"
                  ? !m.endsWith("CORNERS")
                  : corners
                    ? m.endsWith("CORNERS")
                    : true,
              ).map((m) => (
                <option key={m} value={m}>
                  {marketName(m)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Casa
            <select
              value={bookmaker}
              onChange={(e) => setBookmaker(e.target.value)}
            >
              <option value="ALL">Mejor disponible</option>
              {BOOKMAKERS.map((b) => (
                <option key={b}>{b}</option>
              ))}
            </select>
          </label>
          <label>
            Cuota mín.
            <input
              aria-label="Cuota mínima"
              type="number"
              min="1.01"
              step="0.05"
              value={minOdds}
              onChange={(e) => setMinOdds(e.target.value)}
            />
          </label>
          <label>
            Mostrar
            <select value={topN} onChange={(e) => setTopN(e.target.value)}>
              {[5, 10, 20, 0].map((n) => (
                <option key={n} value={n}>
                  {n ? `Top ${n}` : "Todos"}
                </option>
              ))}
            </select>
          </label>
        </div>
        <details className="advanced-filters">
          <summary>
            <SlidersHorizontal size={14} /> Filtros avanzados
          </summary>
          <div className="filter-grid">
            <label>
              País
              <select
                value={country}
                onChange={(e) => {
                  setCountry(e.target.value);
                  setLeague("");
                }}
              >
                <option value="">Todos</option>
                {Array.from(new Set(data?.fixtures.map((f) => f.country)))
                  .sort()
                  .map((c) => (
                    <option key={c}>{c}</option>
                  ))}
              </select>
            </label>
            <label>
              Liga
              <select
                value={league}
                onChange={(e) => setLeague(e.target.value)}
              >
                <option value="">Todas</option>
                {Array.from(
                  new Map(
                    data?.fixtures
                      .filter((f) => !country || f.country === country)
                      .map((f) => [f.league_id, f.league_name]),
                  ),
                ).map(([id, name]) => (
                  <option key={id} value={id}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
            {[
              ["Probabilidad mín. %", minProb, setMinProb],
              ["Cuota máx.", maxOdds, setMaxOdds],
              ["Edge mín. pp", minEdge, setMinEdge],
              ["EV mín. %", minEv, setMinEv],
            ].map(([label, value, setter]) => (
              <label key={String(label)}>
                {String(label)}
                <input
                  type="number"
                  value={String(value)}
                  onChange={(e) =>
                    (setter as (value: string) => void)(e.target.value)
                  }
                />
              </label>
            ))}
            <label>
              Desde
              <input
                type="time"
                value={from}
                onChange={(e) => setFrom(e.target.value)}
              />
            </label>
            <label>
              Hasta
              <input
                type="time"
                value={to}
                onChange={(e) => setTo(e.target.value)}
              />
            </label>
            <label>
              Confianza
              <select
                value={minConfidence}
                onChange={(e) => setMinConfidence(e.target.value)}
              >
                <option value="">Predeterminada en Top</option>
                {["LOW", "MEDIUM", "HIGH", "VERY_HIGH"].map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </label>
            <label>
              Calidad
              <select
                value={minQuality}
                onChange={(e) => setMinQuality(e.target.value)}
              >
                <option value="">Predeterminada en Top</option>
                {["LOW", "ACCEPTABLE", "GOOD", "EXCELLENT"].map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </label>
          </div>
          <div className="checks">
            <label>
              <input
                type="checkbox"
                checked={notStarted}
                onChange={(e) => setNotStarted(e.target.checked)}
              />{" "}
              Solo no iniciados en la tabla
            </label>
            <label>
              <input
                type="checkbox"
                checked={applyOdds}
                onChange={(e) => setApplyOdds(e.target.checked)}
              />{" "}
              Aplicar filtro de cuotas a todos los partidos
            </label>
          </div>
        </details>
      </section>
      {loading && !data ? (
        <Loading />
      ) : (
        <>
          <section className="picks-section">
            <div className="section-heading">
              <div>
                <span className="eyebrow">SELECCIÓN DEL MODELO</span>
                <h2>
                  {topN === "0" ? "Top Picks" : `Top ${topN}`} ·{" "}
                  {marketName(market)}
                </h2>
              </div>
              <span className="subtle">
                Cuota ≥ {minOdds} · Antes del inicio
              </span>
            </div>
            <ErrorMessage message={topError} />
            {picks?.length ? (
              <div className="picks-grid">
                {picks.map((p) => (
                  <PickCard pick={p} key={p.fixture.fixture_id} />
                ))}
              </div>
            ) : (
              <Empty
                title="Sin selecciones que cumplan los filtros"
                text="El Top necesita cuota reciente, confianza y datos suficientes. Puedes consultar todos los encuentros debajo."
              />
            )}
          </section>
          {(section === "/" || section === "/top") && (
            <div className="other-tops">
              {Object.entries(data?.top_groups ?? {})
                .filter(([key]) => key !== market)
                .map(([key, items]) => (
                  <button key={key} onClick={() => setMarket(key)}>
                    <span>{marketName(key)}</span>
                    <b>
                      {items.length} picks <ArrowRight size={13} />
                    </b>
                  </button>
                ))}
            </div>
          )}
          <section className="all-matches">
            <div className="section-heading">
              <div>
                <span className="eyebrow">CARTELERA COMPLETA</span>
                <h2>
                  Todos los partidos{" "}
                  <span className="count">{filtered.length}</span>
                </h2>
              </div>
              <span className="subtle">Ordena pulsando cualquier columna</span>
            </div>
            <FixturesTable rows={filtered} market={market} />
            <div className="table-foot">
              {filtered.length} de {data?.fixtures_found ?? 0} partidos · —
              significa dato no disponible. Probabilidad y confianza son medidas
              diferentes.
            </div>
          </section>
          {section === "/odds" && (
            <ManualOdds
              fixtures={data?.fixtures ?? []}
              onSaved={() => {
                reload();
                reloadTop();
              }}
            />
          )}
        </>
      )}
    </>
  );
}

import { FixtureCard } from "@/components/FixtureCard";
import { RefreshButton } from "@/components/RefreshButton";
import { getDailyAnalysis } from "@/lib/api";
import type { DailyAnalysis } from "@/lib/types";
import Link from "next/link";

function madridToday() {
  return new Intl.DateTimeFormat("en-CA", {
    year: "numeric", month: "2-digit", day: "2-digit", timeZone: "Europe/Madrid",
  }).format(new Date());
}

const timeFormatter = new Intl.DateTimeFormat("es-ES", {
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "Europe/Madrid",
});

type Search = {
  date?: string;
  region?: string;
  quality?: string;
  signal?: string;
  q?: string;
};

function signalHref(selectedDate: string, params: Search, signal: string) {
  const query = new URLSearchParams({ date: selectedDate });
  if (params.q) query.set("q", params.q);
  if (params.region && params.region !== "Todas") query.set("region", params.region);
  if (params.quality && params.quality !== "Todas") query.set("quality", params.quality);
  if (signal !== "Todas") query.set("signal", signal);
  return `/?${query.toString()}#partidos`;
}

export default async function Home({ searchParams }: { searchParams: Promise<Search> }) {
  const params = await searchParams;
  const selectedDate = params.date ?? madridToday();
  let data: DailyAnalysis;
  try {
    data = await getDailyAnalysis(selectedDate);
  } catch (error) {
    return (
      <main className="shell error-shell">
        <p className="eyebrow">CONEXIÓN INTERRUMPIDA</p>
        <h1>No podemos hablar con la API.</h1>
        <p>Comprueba que Docker Desktop esté iniciado y abre de nuevo MatchLab.</p>
        <pre>{error instanceof Error ? error.message : "Error desconocido"}</pre>
      </main>
    );
  }

  const query = (params.q ?? "").trim().toLocaleLowerCase("es");
  const visible = data.fixtures
    .filter((fixture) => !params.region || params.region === "Todas" || fixture.competition.region === params.region)
    .filter((fixture) => !params.quality || params.quality === "Todas" || fixture.prediction?.data_quality === params.quality)
    .filter((fixture) => {
      if (!params.signal || params.signal === "Todas") return true;
      if (params.signal === "Con señal") return Boolean(fixture.prediction?.recommendations.length);
      if (params.signal === "Valor") return fixture.prediction?.recommendations.some((item) => item.kind === "valor");
      if (params.signal === "Alta confianza") return (fixture.prediction?.confidence ?? 0) >= 0.75;
      return true;
    })
    .filter((fixture) => !query || `${fixture.home_team.name} ${fixture.away_team.name} ${fixture.competition.name} ${fixture.competition.country}`.toLocaleLowerCase("es").includes(query))
    .sort((a, b) => a.kickoff_at.localeCompare(b.kickoff_at) || b.competition.priority - a.competition.priority);
  const groups = Map.groupBy(visible, (fixture) => fixture.kickoff_at);
  const analyzed = data.fixtures.filter((fixture) => fixture.prediction);
  const averageGoals = analyzed.length
    ? analyzed.reduce((total, fixture) => total + (fixture.prediction?.total_expected_goals ?? 0), 0) / analyzed.length
    : 0;
  const averageConfidence = analyzed.length
    ? analyzed.reduce((total, fixture) => total + (fixture.prediction?.confidence ?? 0), 0) / analyzed.length
    : 0;
  const openGames = analyzed.filter((fixture) => (fixture.prediction?.over_2_5_probability ?? 0) >= 0.6).length;
  const bttsGames = analyzed.filter((fixture) => (fixture.prediction?.btts_probability ?? 0) >= 0.6).length;
  const featured = data.fixtures
    .map((fixture) => ({ fixture, recommendation: fixture.prediction?.recommendations[0] }))
    .filter((item) => item.recommendation)
    .sort((a, b) => {
      const aValue = a.recommendation?.kind === "valor" ? 1 : 0;
      const bValue = b.recommendation?.kind === "valor" ? 1 : 0;
      return bValue - aValue || (b.recommendation?.signal_score ?? 0) - (a.recommendation?.signal_score ?? 0);
    })
    .slice(0, 3);
  const formattedDate = new Intl.DateTimeFormat("es-ES", { dateStyle: "full", timeZone: "UTC" }).format(new Date(`${selectedDate}T12:00:00Z`));
  const lastUpdated = data.last_updated_at
    ? new Intl.DateTimeFormat("es-ES", {
        dateStyle: "short",
        timeStyle: "short",
        timeZone: "Europe/Madrid",
      }).format(new Date(data.last_updated_at))
    : "pendiente";
  const selectedSignal = params.signal ?? "Todas";
  const filtersActive = Boolean(
    params.q ||
    (params.region && params.region !== "Todas") ||
    (params.quality && params.quality !== "Todas") ||
    (params.signal && params.signal !== "Todas"),
  );

  return (
    <main className="shell">
      <section className="hero">
        <div>
          <p className="eyebrow"><span className="eyebrow-dot" /> CENTRO MUNDIAL DE ANÁLISIS</p>
          <h1>Entiende el partido<br /><em>antes de que empiece.</em></h1>
          <p className="hero-copy">Partidos en orden de inicio, probabilidades fáciles de comparar y señales explicadas. Todo lo importante de la jornada, sin ruido.</p>
          <div className="hero-points" aria-label="Características principales">
            <span>26 mercados</span>
            <span>Cuotas justas</span>
            <span>Actualización continua</span>
          </div>
        </div>
        <div className="date-panel">
          <div className="date-panel-head">
            <span className="calendar-icon" aria-hidden="true">◫</span>
            <div>
              <label htmlFor="date">Jornada analizada</label>
              <small>Elige el día que quieres estudiar</small>
            </div>
          </div>
          <form>
            <input id="date" name="date" type="date" defaultValue={selectedDate} />
            <button type="submit">Ver jornada <span aria-hidden="true">→</span></button>
          </form>
          <RefreshButton date={selectedDate} />
        </div>
      </section>

      {data.demo_mode && <div className="demo-banner"><span className="banner-icon" aria-hidden="true">D</span><div><b>Modo demostración</b><span>Los datos son simulados. Añade tu API_FOOTBALL_KEY al archivo .env para descargar la cartelera mundial real.</span></div></div>}
      <div className={`update-status ${data.automatic_refresh ? "active" : "inactive"}`}>
        <span>{data.automatic_refresh ? "Actualización automática activa" : "Actualización real pendiente de clave"}</span>
        <b>Última actualización: {lastUpdated}</b>
        <small>{data.automatic_refresh ? `Actualización completa cada ${data.automatic_refresh_minutes} minutos mientras MatchLab esté abierto` : `Configurada cada ${data.automatic_refresh_minutes} minutos; se activará al añadir la clave real`}</small>
      </div>

      <section className="summary" id="resumen">
        <div><span>Por comenzar</span><strong>{data.total_fixtures}</strong></div>
        <div><span>Analizados</span><strong>{data.analyzed_fixtures}</strong></div>
        <div><span>Con señal</span><strong>{data.recommended_fixtures}</strong></div>
        <div><span>Fecha</span><strong className="date-stat">{formattedDate}</strong></div>
      </section>

      <section className="daily-intelligence">
        <div className="section-title">
          <div><p className="eyebrow">LECTURA RÁPIDA</p><h2>Radiografía de la jornada</h2></div>
          <span>Calculada sobre {analyzed.length} partidos analizados</span>
        </div>
        <div className="pulse-grid">
          <article><span>Media de goles esperados</span><strong>{averageGoals.toFixed(2)}</strong><small>por partido</small></article>
          <article><span>Confianza media</span><strong>{Math.round(averageConfidence * 100)}%</strong><small>cobertura del modelo</small></article>
          <article><span>Partidos abiertos</span><strong>{openGames}</strong><small>≥ 60% de más de 2,5</small></article>
          <article><span>Ambos marcan</span><strong>{bttsGames}</strong><small>≥ 60% de probabilidad</small></article>
        </div>
        {featured.length > 0 && (
          <div className="featured-signals">
            <div className="featured-label">Señales destacadas</div>
            {featured.map(({ fixture, recommendation }) => (
              <Link href={`/partidos/${fixture.id}`} key={fixture.id}>
                <span>{recommendation?.kind === "valor" ? "Valor" : "Tendencia"}</span>
                <b>{fixture.home_team.name} – {fixture.away_team.name}</b>
                <small>
                  {recommendation?.selection} · {Math.round((recommendation?.probability ?? 0) * 100)}%
                  {recommendation?.fair_odds ? ` · justa ${recommendation.fair_odds.toFixed(2)}` : ""}
                </small>
              </Link>
            ))}
          </div>
        )}
      </section>

      {data.demo_mode && (
        <section className="data-readiness">
          <div className="readiness-copy">
            <p className="eyebrow">PREPARADO PARA DATOS REALES</p>
            <h2>El sistema ya está listo para la clave.</h2>
            <p>Mientras llega, puedes recorrer toda la experiencia con datos de demostración. Al añadirla no cambiará la forma de usar MatchLab: solo se sustituirá la fuente simulada por la cartelera real.</p>
          </div>
          <div className="readiness-steps" aria-label="Estado de preparación">
            <div className="complete"><span>1</span><p><b>Interfaz</b><small>Lista y responsive</small></p></div>
            <div className="complete"><span>2</span><p><b>Modelos</b><small>Probados y versionados</small></p></div>
            <div className="pending"><span>3</span><p><b>API key</b><small>Pendiente de conectar</small></p></div>
          </div>
        </section>
      )}

      <div className="match-tools">
        <div>
          <p className="eyebrow">ENCUENTRA LO IMPORTANTE</p>
          <h2>Explora la jornada</h2>
        </div>
        <div className="quick-filters" aria-label="Filtros rápidos de señal">
          {[
            ["Todas", "Todos"],
            ["Con señal", "Con señal"],
            ["Valor", "Valor"],
            ["Alta confianza", "Alta confianza"],
          ].map(([value, label]) => (
            <Link
              key={value}
              href={signalHref(selectedDate, params, value)}
              className={selectedSignal === value ? "active" : ""}
            >
              {label}
            </Link>
          ))}
        </div>
      </div>

      <form className="filters" aria-label="Filtros de partidos">
        <input type="hidden" name="date" value={selectedDate} />
        <label className="filter-field search-field">
          <span>Buscar</span>
          <input name="q" defaultValue={params.q} placeholder="Equipo o competición" />
        </label>
        <label className="filter-field">
          <span>Región</span>
          <select name="region" defaultValue={params.region ?? "Todas"}>
            {["Todas", "Europa", "América", "Asia", "África", "Mundo", "Otros"].map((region) => <option key={region}>{region}</option>)}
          </select>
        </label>
        <label className="filter-field">
          <span>Datos</span>
          <select name="quality" defaultValue={params.quality ?? "Todas"}>
            <option value="Todas">Cualquier calidad</option>
            <option value="alta">Calidad alta</option>
            <option value="media">Calidad media</option>
            <option value="baja">Calidad baja</option>
          </select>
        </label>
        <label className="filter-field">
          <span>Señal</span>
          <select name="signal" defaultValue={params.signal ?? "Todas"}>
            <option value="Todas">Todas las señales</option>
            <option value="Con señal">Con recomendación</option>
            <option value="Valor">Solo valor detectado</option>
            <option value="Alta confianza">Alta confianza</option>
          </select>
        </label>
        <div className="filter-actions">
          <button type="submit">Aplicar filtros</button>
          {filtersActive && <Link href={`/?date=${selectedDate}#partidos`}>Limpiar</Link>}
        </div>
      </form>

      <details className="reading-guide">
        <summary>
          <span>¿Cómo se lee una tarjeta?</span>
          <small>Guía rápida de probabilidades y señales</small>
        </summary>
        <div className="reading-guide-grid">
          <div><i className="guide-icon outcomes">1X2</i><p><b>Probabilidad de resultado</b><span>1 es local, X empate y 2 visitante. La barra permite comparar el reparto de un vistazo.</span></p></div>
          <div><i className="guide-icon quality-guide">A</i><p><b>Calidad de datos</b><span>Mide cobertura y muestra disponible. No significa probabilidad de acertar.</span></p></div>
          <div><i className="guide-icon value-guide">V</i><p><b>Valor y tendencia</b><span>Solo hay valor con cuota real y ventaja suficiente; sin cuota se muestra una tendencia.</span></p></div>
        </div>
      </details>

      <section className="matches-section" id="partidos">
        <div className="section-title"><div><p className="eyebrow">{data.timezone}</p><h2>Horario de próximos partidos</h2></div><span>{visible.length} de {data.total_fixtures} encuentros</span></div>
        {visible.length === 0 && (
          <div className="empty">
            <h3>{data.total_fixtures === 0 ? "No quedan partidos por comenzar." : "Ningún partido coincide con los filtros."}</h3>
            <p>{data.total_fixtures === 0 ? "Elige mañana o pulsa Actualizar datos." : "Amplía la región, la calidad o la búsqueda."}</p>
          </div>
        )}
        {[...groups.entries()].map(([kickoff, fixtures], index) => (
          <div className="time-group" key={kickoff}>
            <h3>
              <time dateTime={kickoff}>{timeFormatter.format(new Date(kickoff))}</time>
              <span>{fixtures.length} {fixtures.length === 1 ? "partido" : "partidos"}</span>
              {index === 0 && <em>Lo siguiente</em>}
            </h3>
            <div className="fixture-list">{fixtures.map((fixture) => <FixtureCard key={fixture.id} fixture={fixture} />)}</div>
          </div>
        ))}
      </section>
    </main>
  );
}

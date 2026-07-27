import { FixtureCard } from "@/components/FixtureCard";
import { RefreshButton } from "@/components/RefreshButton";
import { getDailyAnalysis } from "@/lib/api";
import type { DailyAnalysis } from "@/lib/types";

function madridToday() {
  return new Intl.DateTimeFormat("en-CA", {
    year: "numeric", month: "2-digit", day: "2-digit", timeZone: "Europe/Madrid",
  }).format(new Date());
}

export default async function Home({ searchParams }: { searchParams: Promise<{ date?: string }> }) {
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
        <p>Comprueba que Docker Desktop esté iniciado y ejecuta <code>.\scripts\start.ps1</code>.</p>
        <pre>{error instanceof Error ? error.message : "Error desconocido"}</pre>
      </main>
    );
  }

  const groups = Map.groupBy(data.fixtures, (fixture) => `${fixture.competition.country ?? "Mundo"} · ${fixture.competition.name}`);
  const formattedDate = new Intl.DateTimeFormat("es-ES", { dateStyle: "full", timeZone: "UTC" }).format(new Date(`${selectedDate}T12:00:00Z`));

  return (
    <main className="shell">
      <section className="hero">
        <div>
          <p className="eyebrow">CENTRO DE ANÁLISIS DIARIO</p>
          <h1>Los partidos de hoy,<br /><em>puestos en contexto.</em></h1>
          <p className="hero-copy">Forma reciente, fortaleza de cada equipo y distribuciones de goles y córners. Cada cifra lleva su nivel de confianza.</p>
        </div>
        <div className="date-panel">
          <label htmlFor="date">Jornada analizada</label>
          <form><input id="date" name="date" type="date" defaultValue={selectedDate} /><button type="submit">Ver fecha</button></form>
          <RefreshButton date={selectedDate} />
        </div>
      </section>

      {data.demo_mode && <div className="demo-banner"><b>Modo demostración</b><span>Los datos son simulados. Añade tu API_FOOTBALL_KEY al archivo .env para obtener partidos reales.</span></div>}

      <section className="summary">
        <div><span>Partidos</span><strong>{data.total_fixtures}</strong></div>
        <div><span>Analizados</span><strong>{data.analyzed_fixtures}</strong></div>
        <div><span>Confianza alta</span><strong>{data.high_confidence_fixtures}</strong></div>
        <div><span>Fecha</span><strong className="date-stat">{formattedDate}</strong></div>
      </section>

      <section className="matches-section">
        <div className="section-title"><div><p className="eyebrow">{data.timezone}</p><h2>Cartelera completa</h2></div><span>{data.total_fixtures} encuentros</span></div>
        {data.total_fixtures === 0 && <div className="empty"><h3>No hay partidos almacenados para esta fecha.</h3><p>Actualiza los datos o comprueba la cobertura de tu proveedor.</p></div>}
        {[...groups.entries()].map(([competition, fixtures]) => (
          <div className="competition" key={competition}>
            <h3>{competition}<span>{fixtures.length}</span></h3>
            <div className="fixture-list">{fixtures.map((fixture) => <FixtureCard key={fixture.id} fixture={fixture} />)}</div>
          </div>
        ))}
      </section>
    </main>
  );
}

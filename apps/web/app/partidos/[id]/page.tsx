import Link from "next/link";
import { getFixture } from "@/lib/api";

const pct = (value: number | null) => value === null ? "—" : `${Math.round(value * 100)}%`;
const selectionLabel: Record<string, string> = {
  Home: "Victoria local", Draw: "Empate", Away: "Victoria visitante",
  "Over 2.5": "Más de 2,5 goles", "Under 2.5": "Menos de 2,5 goles",
  "BTTS Yes": "Ambos equipos marcan", "BTTS No": "No marcan ambos",
  "Over 8.5": "Más de 8,5 córners", "Under 8.5": "Menos de 8,5 córners",
  "Over 9.5": "Más de 9,5 córners", "Under 9.5": "Menos de 9,5 córners",
};

export default async function FixturePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const fixture = await getFixture(id);
  const p = fixture.prediction;

  return (
    <main className="shell detail-shell">
      <Link href="/" className="back">← Volver a todos los partidos</Link>
      <div className="detail-kicker">{fixture.competition.region} · {fixture.competition.country} · {fixture.competition.name}</div>
      <section className="scoreboard">
        <div><span>LOCAL</span><h1>{fixture.home_team.name}</h1></div>
        <div className="kickoff"><b>{new Intl.DateTimeFormat("es-ES", { dateStyle: "medium", timeStyle: "short", timeZone: "Europe/Madrid" }).format(new Date(fixture.kickoff_at))}</b><span>{fixture.venue_name ?? "Sede por confirmar"}</span></div>
        <div className="right"><span>VISITANTE</span><h1>{fixture.away_team.name}</h1></div>
      </section>
      {!p ? <div className="empty"><h3>Este partido todavía no tiene análisis.</h3></div> : (
        <>
          {p.recommendations.length > 0 ? (
            <section className="recommendations">
              <div className="section-title"><div><p className="eyebrow">SEÑALES DEL MODELO</p><h2>Recomendaciones</h2></div><span>No garantizan beneficio</span></div>
              <div className="recommendation-grid">
                {p.recommendations.map((item) => (
                  <article key={`${item.market}-${item.selection}`} className={item.kind}>
                    <span>{item.kind === "valor" ? `Valor · ${item.rating}` : "Tendencia estadística"}</span>
                    <h3>{selectionLabel[item.selection] ?? item.selection}</h3>
                    <strong>{pct(item.probability)}</strong>
                    {item.decimal_odds && <p>Cuota {item.decimal_odds.toFixed(2)} · {item.bookmaker}</p>}
                    {item.expected_value !== null && <p>Valor esperado estimado: {pct(item.expected_value)}</p>}
                    <small>{item.rationale}</small>
                  </article>
                ))}
              </div>
            </section>
          ) : <div className="caution">No se publica una recomendación: la confianza o la ventaja estimada no supera el mínimo exigido.</div>}

          <div className="detail-grid">
            <section className="analysis-panel accent-panel"><p className="eyebrow">MODELO DE GOLES</p><h2>{p.total_expected_goals.toFixed(2)}</h2><p>goles esperados totales</p><div className="split"><span>{fixture.home_team.name}<b>{p.home_expected_goals.toFixed(2)}</b></span><span>{fixture.away_team.name}<b>{p.away_expected_goals.toFixed(2)}</b></span></div></section>
            <section className="analysis-panel"><p className="eyebrow">MODELO DE CÓRNERS</p><h2>{p.total_expected_corners?.toFixed(2) ?? "—"}</h2><p>córners esperados totales</p><div className="split"><span>{fixture.home_team.name}<b>{p.home_expected_corners?.toFixed(2) ?? "s/d"}</b></span><span>{fixture.away_team.name}<b>{p.away_expected_corners?.toFixed(2) ?? "s/d"}</b></span></div></section>
          </div>
          <section className="markets">
            <h2>Probabilidades del partido</h2>
            <div className="market-grid"><div><span>Victoria local</span><b>{pct(p.home_win_probability)}</b></div><div><span>Empate</span><b>{pct(p.draw_probability)}</b></div><div><span>Victoria visitante</span><b>{pct(p.away_win_probability)}</b></div><div><span>Más de 2,5 goles</span><b>{pct(p.over_2_5_probability)}</b></div><div><span>Ambos marcan</span><b>{pct(p.btts_probability)}</b></div><div><span>Más de 9,5 córners</span><b>{pct(p.over_9_5_corners_probability)}</b></div></div>
          </section>
          <section className="team-insights">
            {p.team_insights.map((team) => <article key={team.team_id}><span>{team.venue}</span><h3>{team.team_name}</h3><p>{team.summary}</p><div><b>{pct(team.win_probability)}</b> gana <b>{pct(team.avoid_defeat_probability)}</b> no pierde</div></article>)}
          </section>
          <div className="detail-grid lower">
            <section className="analysis-panel"><p className="eyebrow">MARCADORES MÁS PROBABLES</p><div className="scores">{p.likely_scores.map((score) => <div key={score.score}><strong>{score.score}</strong><span>{pct(score.probability)}</span></div>)}</div></section>
            <section className="analysis-panel"><p className="eyebrow">POR QUÉ DICE ESTO EL MODELO</p><ul className="reasons">{p.explanation.map((reason) => <li key={reason}>{reason}</li>)}</ul><div className={`quality large ${p.data_quality}`}>Calidad {p.data_quality} · confianza {pct(p.confidence)}</div></section>
          </div>
        </>
      )}
    </main>
  );
}

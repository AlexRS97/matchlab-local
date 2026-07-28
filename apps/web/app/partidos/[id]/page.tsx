import Link from "next/link";
import { getFixture } from "@/lib/api";
import type { MarketProbability } from "@/lib/types";

const pct = (value: number | null) =>
  value === null ? "—" : `${Math.round(value * 100)}%`;

const selectionLabel: Record<string, string> = {
  Home: "Victoria local",
  Draw: "Empate",
  Away: "Victoria visitante",
  "Over 2.5": "Más de 2,5 goles",
  "Under 2.5": "Menos de 2,5 goles",
  "BTTS Yes": "Ambos equipos marcan",
  "BTTS No": "No marcan ambos",
  "Over 8.5": "Más de 8,5 córners",
  "Under 8.5": "Menos de 8,5 córners",
  "Over 9.5": "Más de 9,5 córners",
  "Under 9.5": "Menos de 9,5 córners",
};

const marketOrder = [
  "Resultado",
  "Doble oportunidad",
  "Goles totales",
  "Ambos marcan",
  "Goles por equipo",
  "Portería a cero",
  "Córners totales",
];

function DetailTeamLogo({ name, url }: { name: string; url: string | null }) {
  return url
    ? <img src={url} alt="" className="scoreboard-logo" />
    : <span className="scoreboard-fallback">{name[0]}</span>;
}

function MarketGroup({
  name,
  markets,
}: {
  name: string;
  markets: MarketProbability[];
}) {
  return (
    <article className="market-family">
      <h3>{name}</h3>
      {markets.map((market) => (
        <div className="market-line" key={market.key}>
          <span>{market.selection}</span>
          <div className="mini-meter">
            <i style={{ width: pct(market.probability) }} />
          </div>
          <b>{pct(market.probability)}</b>
          <small>{market.fair_odds ? `justa ${market.fair_odds.toFixed(2)}` : "—"}</small>
        </div>
      ))}
    </article>
  );
}

export default async function FixturePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const fixture = await getFixture(id);
  const p = fixture.prediction;

  if (!p) {
    return (
      <main className="shell detail-shell">
        <Link href="/" className="back">← Volver a todos los partidos</Link>
        <div className="empty detail-empty">
          <h3>Este partido todavía no tiene análisis.</h3>
          <p>Se calculará automáticamente cuando haya datos históricos suficientes.</p>
        </div>
      </main>
    );
  }

  const favoriteName =
    p.favorite === "home"
      ? fixture.home_team.name
      : p.favorite === "away"
        ? fixture.away_team.name
        : "Empate";
  const marketGroups = Map.groupBy(p.market_probabilities, (market) => market.category);
  const homeScores = [0, 1, 2, 3, 4];
  const awayScores = [0, 1, 2, 3, 4];

  return (
    <main className="shell detail-shell">
      <div className="detail-nav">
        <Link href="/#partidos" className="back"><span aria-hidden="true">←</span> Todos los partidos</Link>
        <div className="detail-nav-badges">
          {fixture.provider_id < 0 && <span className="demo-detail-pill">Datos demo</span>}
          <span className="detail-nav-status"><i /> Análisis actualizado</span>
        </div>
      </div>
      <div className="detail-kicker">
        {fixture.competition.region} · {fixture.competition.country} · {fixture.competition.name}
      </div>
      <section className="scoreboard">
        <div className="scoreboard-team">
          <DetailTeamLogo name={fixture.home_team.name} url={fixture.home_team.logo_url} />
          <span>LOCAL</span>
          <h1>{fixture.home_team.name}</h1>
        </div>
        <div className="kickoff">
          <strong className="versus-badge">VS</strong>
          <b>
            {new Intl.DateTimeFormat("es-ES", {
              dateStyle: "medium",
              timeStyle: "short",
              timeZone: "Europe/Madrid",
            }).format(new Date(fixture.kickoff_at))}
          </b>
          <span>{fixture.venue_name ?? "Sede por confirmar"}</span>
        </div>
        <div className="scoreboard-team right">
          <DetailTeamLogo name={fixture.away_team.name} url={fixture.away_team.logo_url} />
          <span>VISITANTE</span>
          <h1>{fixture.away_team.name}</h1>
        </div>
      </section>

      <section className="match-profile">
        <div>
          <span>Resultado más probable</span>
          <strong>{favoriteName}</strong>
          <small>{pct(p.favorite_probability)} de probabilidad</small>
          <i style={{ "--value": pct(p.favorite_probability) } as React.CSSProperties} />
        </div>
        <div>
          <span>Claridad del pronóstico</span>
          <strong>{pct(p.result_clarity)}</strong>
          <small>{pct(p.outcome_uncertainty)} de incertidumbre 1X2</small>
          <i style={{ "--value": pct(p.result_clarity) } as React.CSSProperties} />
        </div>
        <div>
          <span>Puntos esperados</span>
          <strong>{p.home_expected_points.toFixed(2)} – {p.away_expected_points.toFixed(2)}</strong>
          <small>local frente a visitante</small>
          <i style={{ "--value": "100%" } as React.CSSProperties} />
        </div>
        <div>
          <span>Fuerza de señal</span>
          <strong>{pct(p.signal_strength)}</strong>
          <small>favorito × confianza de datos</small>
          <i style={{ "--value": pct(p.signal_strength) } as React.CSSProperties} />
        </div>
      </section>

      <nav className="analysis-nav" aria-label="Secciones del análisis">
        <a href="#resultado">Resultado</a>
        <a href="#recomendaciones">Recomendaciones</a>
        <a href="#modelos">Goles y córners</a>
        <a href="#mercados">Mercados</a>
        <a href="#marcadores">Marcadores</a>
      </nav>

      <section className="outcome-section" id="resultado">
        <div className="section-title compact">
          <div><p className="eyebrow">DISTRIBUCIÓN 1X2</p><h2>Cómo se reparte el partido</h2></div>
          <span>La anchura representa probabilidad</span>
        </div>
        <div className="outcome-chart">
          <div className="home" style={{ width: pct(p.home_win_probability) }}>
            <span>1</span><b>{pct(p.home_win_probability)}</b>
          </div>
          <div className="draw" style={{ width: pct(p.draw_probability) }}>
            <span>X</span><b>{pct(p.draw_probability)}</b>
          </div>
          <div className="away" style={{ width: pct(p.away_win_probability) }}>
            <span>2</span><b>{pct(p.away_win_probability)}</b>
          </div>
        </div>
      </section>

      {p.recommendations.length > 0 ? (
        <section className="recommendations" id="recomendaciones">
          <div className="section-title">
            <div><p className="eyebrow">SEÑALES DEL MODELO</p><h2>Recomendaciones</h2></div>
            <span>No garantizan beneficio</span>
          </div>
          <div className="recommendation-grid">
            {p.recommendations.map((item) => (
              <article key={`${item.market}-${item.selection}`} className={item.kind}>
                <span>{item.kind === "valor" ? `Valor · ${item.rating}` : "Tendencia estadística"}</span>
                <h3>{selectionLabel[item.selection] ?? item.selection}</h3>
                <strong>{pct(item.probability)}</strong>
                <div className="recommendation-facts">
                  {item.conservative_probability !== null && (
                    <p>Probabilidad conservadora <b>{pct(item.conservative_probability)}</b></p>
                  )}
                  {item.fair_odds !== null && <p>Cuota justa <b>{item.fair_odds.toFixed(2)}</b></p>}
                  {item.decimal_odds && <p>Mejor cuota <b>{item.decimal_odds.toFixed(2)}</b> · {item.bookmaker}</p>}
                  {item.probability_edge !== null && <p>Ventaja probabilística <b>{pct(item.probability_edge)}</b></p>}
                  {item.expected_value !== null && <p>Valor esperado <b>{pct(item.expected_value)}</b></p>}
                </div>
                <small>{item.rationale}</small>
              </article>
            ))}
          </div>
        </section>
      ) : (
        <div className="caution">
          No se publica una recomendación: la confianza o la ventaja estimada no supera el mínimo exigido.
        </div>
      )}

      <div className="detail-grid" id="modelos">
        <section className="analysis-panel accent-panel">
          <p className="eyebrow">MODELO DE GOLES</p>
          <h2>{p.total_expected_goals.toFixed(2)}</h2>
          <p>goles esperados totales</p>
          <div className="split">
            <span>{fixture.home_team.name}<b>{p.home_expected_goals.toFixed(2)}</b></span>
            <span>{fixture.away_team.name}<b>{p.away_expected_goals.toFixed(2)}</b></span>
          </div>
        </section>
        <section className="analysis-panel">
          <p className="eyebrow">MODELO DE CÓRNERS</p>
          <h2>{p.total_expected_corners?.toFixed(2) ?? "—"}</h2>
          <p>córners esperados totales</p>
          <div className="split">
            <span>{fixture.home_team.name}<b>{p.home_expected_corners?.toFixed(2) ?? "s/d"}</b></span>
            <span>{fixture.away_team.name}<b>{p.away_expected_corners?.toFixed(2) ?? "s/d"}</b></span>
          </div>
        </section>
      </div>

      <section className="goal-distribution">
        <div>
          <p className="eyebrow">RANGO DE GOLES</p>
          <h2>Perfil de anotación</h2>
          <p>Una vista más estable que apostar por un marcador exacto.</p>
        </div>
        <div className="goal-bands">
          {p.goal_bands.map((band, index) => (
            <div key={band.label}>
              <span>{band.label}</span>
              <b>{pct(band.probability)}</b>
              <i className={`band-${index}`} style={{ width: pct(band.probability) }} />
            </div>
          ))}
        </div>
      </section>

      <section className="market-explorer" id="mercados">
        <div className="section-title">
          <div><p className="eyebrow">CUOTAS JUSTAS SIN MARGEN</p><h2>Explorador de mercados</h2></div>
          <span>Referencia matemática, no cuota recomendada</span>
        </div>
        <div className="market-families">
          {marketOrder
            .filter((category) => marketGroups.has(category))
            .map((category) => (
              <MarketGroup
                key={category}
                name={category}
                markets={marketGroups.get(category) ?? []}
              />
            ))}
        </div>
      </section>

      <div className="visual-grid" id="marcadores">
        <section className="score-heatmap">
          <div>
            <p className="eyebrow">MATRIZ DE MARCADORES</p>
            <h2>Dónde concentra masa el modelo</h2>
            <small>Filas: goles local · columnas: goles visitante</small>
          </div>
          <div className="score-matrix" aria-label="Matriz de probabilidades de marcador">
            <span className="matrix-corner">L\V</span>
            {awayScores.map((score) => <span className="matrix-head" key={`a-${score}`}>{score}</span>)}
            {homeScores.map((homeScore) => (
              <div className="matrix-row" key={`h-${homeScore}`}>
                <span className="matrix-head">{homeScore}</span>
                {awayScores.map((awayScore) => {
                  const cell = p.score_matrix.find(
                    (item) => item.home_goals === homeScore && item.away_goals === awayScore,
                  );
                  return (
                    <span
                      className="matrix-cell"
                      key={`${homeScore}-${awayScore}`}
                      style={{ "--heat": cell?.relative_intensity ?? 0 } as React.CSSProperties}
                      title={`${homeScore}-${awayScore}: ${pct(cell?.probability ?? 0)}`}
                    >
                      {pct(cell?.probability ?? 0)}
                    </span>
                  );
                })}
              </div>
            ))}
          </div>
        </section>
        <section className="analysis-panel likely-panel">
          <p className="eyebrow">MARCADORES MÁS PROBABLES</p>
          <div className="scores">
            {p.likely_scores.map((score, index) => (
              <div key={score.score}>
                <small>#{index + 1}</small>
                <strong>{score.score}</strong>
                <span>{pct(score.probability)}</span>
              </div>
            ))}
          </div>
          <p className="score-warning">
            Incluso el marcador principal concentra una parte pequeña del total: úsalo como contexto, no como certeza.
          </p>
        </section>
      </div>

      <section className="team-insights">
        {p.team_insights.map((team) => (
          <article key={team.team_id}>
            <span>{team.venue}</span>
            <h3>{team.team_name}</h3>
            <p>{team.summary}</p>
            <div><b>{pct(team.win_probability)}</b> gana <b>{pct(team.avoid_defeat_probability)}</b> no pierde</div>
          </article>
        ))}
      </section>

      <section className="analysis-panel explanation-panel">
        <p className="eyebrow">POR QUÉ DICE ESTO EL MODELO</p>
        <ul className="reasons">{p.explanation.map((reason) => <li key={reason}>{reason}</li>)}</ul>
        <div className={`quality large ${p.data_quality}`}>
          Calidad {p.data_quality} · confianza {pct(p.confidence)} · modelo {p.model_version}
        </div>
      </section>
    </main>
  );
}

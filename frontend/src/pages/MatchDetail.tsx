import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useResource } from "../hooks/useResource";
import {
  MARKETS,
  type Analysis,
  type Comparison,
  type MatchData,
} from "../types";
import { ago, marketName, num, pct, time } from "../utils/format";
import { Badge, Empty, ErrorMessage, Loading } from "../components/Primitives";
import { ModelBreakdown } from "../components/ModelBreakdown";
import { StatsPanel } from "../components/StatsPanel";
import { LearnedPredictions } from "../components/LearnedPredictions";
import { OddsComparison } from "../components/OddsComparison";

export function MatchDetail() {
  const { id } = useParams();
  const { data, error, loading } = useResource<MatchData>(
    `/fixtures/${id}`,
    30000,
  );
  const odds = useResource<Comparison[]>(`/fixtures/${id}/odds`, 15000);
  const analysis = useResource<Analysis>(`/fixtures/${id}/analysis`, 30000);
  const [goalMarket, setGoalMarket] = useState("OVER_2_5_GOALS");
  const [cornerMarket, setCornerMarket] = useState("OVER_9_5_CORNERS");
  if (loading && !data) return <Loading />;
  if (!data)
    return (
      <>
        <Link to="/">Volver a Today</Link>
        <ErrorMessage message={error} />
      </>
    );
  const f = data.fixture,
    p = data.prediction,
    features = p?.features;
  const poisson = p?.goals.models.find((m) => m.name === "poisson");
  const matrix = poisson?.diagnostics.score_matrix as number[][] | undefined;
  const distribution = poisson?.diagnostics.total_distribution as
    number[] | undefined;
  return (
    <>
      <Link className="back-link" to="/">
        <ArrowLeft size={14} /> Volver a la jornada
      </Link>
      <header className="page-header">
        <div>
          <div className="eyebrow">
            {f.country} / {f.league_name}
          </div>
          <h1 className="match-title">
            {f.home_team}
            <span> vs </span>
            {f.away_team}
          </h1>
          <p>
            {new Date(f.kickoff_utc).toLocaleDateString("es-ES", {
              timeZone: "Europe/Madrid",
            })}{" "}
            · {time(f.kickoff_utc)} Europe/Madrid ·{" "}
            {f.status.replaceAll("_", " ")}
          </p>
        </div>
        <div className="subtle">
          Datos {ago(f.updated_at)}
          {p && <small>Predicción {ago(p.timestamp)}</small>}
        </div>
      </header>
      <ErrorMessage message={error || odds.error || analysis.error} />
      {!p?.goals.probabilities.OVER_2_5_GOALS && (
        <Empty
          title="Datos insuficientes para goles"
          text="El sistema necesita al menos cinco partidos anteriores por equipo. Las cuotas y los datos disponibles siguen visibles."
        />
      )}
      {p && (
        <>
          <div className="stats-grid match-stats">
            {[
              ["Over 2.5", pct(p.goals.probabilities.OVER_2_5_GOALS)],
              ["Goles esperados", num(p.goals.expected_total)],
              ["Ambos marcan", pct(p.goals.probabilities.BTTS_YES)],
              ["Córners esperados", num(p.corners.expected_total)],
            ].map(([name, value]) => (
              <div className="stat-card" key={name}>
                <span>{name}</span>
                <strong>{value}</strong>
              </div>
            ))}
            <div className="stat-card">
              <span>Confianza / calidad</span>
              <div className="grade-stack">
                <Badge grade={p.confidence.OVER_2_5_GOALS} />
                <Badge grade={p.quality} />
              </div>
            </div>
          </div>
          <div className="detail-section">
            <div className="section-heading">
              <h2>Modelos de goles</h2>
              <select
                aria-label="Mercado de goles en detalle"
                value={goalMarket}
                onChange={(e) => setGoalMarket(e.target.value)}
              >
                {MARKETS.filter((m) => !m.endsWith("CORNERS")).map((m) => (
                  <option key={m} value={m}>
                    {marketName(m)}
                  </option>
                ))}
              </select>
            </div>
            <div className="two-columns">
              <ModelBreakdown
                ensemble={p.goals}
                market={goalMarket}
                title="Probabilidades por modelo"
              />
              <section className="panel">
                <h2>Distribución de goles · Poisson</h2>
                <p className="subtle">
                  Local {num(p.goals.expected_home)} · Visitante{" "}
                  {num(p.goals.expected_away)} esperados en ensemble
                </p>
                {distribution && (
                  <ResponsiveContainer width="100%" height={210}>
                    <BarChart
                      data={distribution.map((value, i) => ({
                        goles: i === 5 ? "5+" : String(i),
                        probabilidad: Math.round(value * 1000) / 10,
                      }))}
                    >
                      <XAxis
                        dataKey="goles"
                        tick={{ fill: "#93a4bd", fontSize: 11 }}
                      />
                      <YAxis
                        tick={{ fill: "#93a4bd", fontSize: 10 }}
                        unit="%"
                      />
                      <Tooltip
                        contentStyle={{
                          background: "#142031",
                          border: "1px solid #30425a",
                        }}
                      />
                      <Bar
                        dataKey="probabilidad"
                        fill="#80b7c5"
                        radius={[5, 5, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                )}
                {matrix && (
                  <>
                    <h3>Matriz de marcadores</h3>
                    <div className="score-matrix">
                      <span>Local ↓ / Vis. →</span>
                      {Array.from({ length: 7 }, (_, i) => (
                        <b key={i}>{i}</b>
                      ))}
                      {matrix.map((row, i) => (
                        <div className="matrix-row" key={i}>
                          <b>{i}</b>
                          {row.map((value, j) => (
                            <span
                              key={j}
                              style={{
                                background: `rgba(198,246,107,${value * 4})`,
                              }}
                              title={`${i}–${j}: ${pct(value)}`}
                            >
                              {(value * 100).toFixed(1)}%
                            </span>
                          ))}
                        </div>
                      ))}
                    </div>
                    <p className="subtle">
                      Cola fuera de 0–6:{" "}
                      {pct(poisson?.diagnostics.residual_tail as number)}.
                      Ningún marcador se considera seguro.
                    </p>
                  </>
                )}
              </section>
            </div>
          </div>
          {features && (
            <div className="detail-section">
              <StatsPanel
                features={features}
                home={f.home_team}
                away={f.away_team}
              />
            </div>
          )}
          {features && (
            <div className="two-columns detail-section">
              <section className="panel">
                <h2>Clasificación</h2>
                {features.standings.length ? (
                  <div className="table-scroll">
                    <table className="detail-table">
                      <thead>
                        <tr>
                          {[
                            "#",
                            "Equipo",
                            "PJ",
                            "Pts",
                            "G",
                            "E",
                            "P",
                            "GF",
                            "GA",
                            "DG",
                          ].map((v) => (
                            <th key={v}>{v}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {features.standings.map((s, index) => (
                          <tr
                            key={`${s.team_id}-${index}`}
                            className={
                              [f.home_team_id, f.away_team_id].includes(
                                s.team_id,
                              )
                                ? "highlight-row"
                                : ""
                            }
                          >
                            <td>{s.position}</td>
                            <td>{s.team}</td>
                            <td>{s.played}</td>
                            <td>{s.points}</td>
                            <td>{s.wins}</td>
                            <td>{s.draws}</td>
                            <td>{s.losses}</td>
                            <td>{s.goals_for}</td>
                            <td>{s.goals_against}</td>
                            <td>{s.goal_difference}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="subtle">
                    Sin clasificación disponible anterior al inicio.
                  </p>
                )}
                {features.league && (
                  <p className="subtle">
                    Liga: {num(features.league.total_goals_average)} goles ·
                    Over 2.5 {pct(features.league.over25_rate)} · BTTS{" "}
                    {pct(features.league.btts_rate)} · Muestra{" "}
                    {features.league.sample_size}
                  </p>
                )}
              </section>
              <section className="panel">
                <h2>Enfrentamientos directos</h2>
                <p className="subtle">
                  Muestra: {features.h2h.summary.sample_size} · Over 2.5{" "}
                  {pct(features.h2h.summary.over25_rate)} · BTTS{" "}
                  {pct(features.h2h.summary.btts_rate)}
                </p>
                {features.h2h.matches.length ? (
                  <table className="detail-table">
                    <thead>
                      <tr>
                        <th>Fecha</th>
                        <th>Resultado local de hoy</th>
                        <th>Competición</th>
                        <th>Córners</th>
                      </tr>
                    </thead>
                    <tbody>
                      {features.h2h.matches.map((m) => (
                        <tr key={m.fixture_id}>
                          <td>
                            {new Date(m.kickoff_utc).toLocaleDateString(
                              "es-ES",
                            )}
                          </td>
                          <td>
                            {m.goals_for}–{m.goals_against} (
                            {m.is_home ? "casa" : "fuera"})
                          </td>
                          <td>{m.competition}</td>
                          <td>
                            {m.corners_for != null && m.corners_against != null
                              ? m.corners_for + m.corners_against
                              : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p className="subtle">
                    No hay H2H guardados. No se asigna peso a datos ausentes.
                  </p>
                )}
              </section>
            </div>
          )}
          <div className="detail-section">
            <div className="section-heading">
              <h2>Análisis de córners</h2>
              <select
                aria-label="Mercado de córners en detalle"
                value={cornerMarket}
                onChange={(e) => setCornerMarket(e.target.value)}
              >
                {MARKETS.filter((m) => m.endsWith("CORNERS")).map((m) => (
                  <option key={m} value={m}>
                    {marketName(m)}
                  </option>
                ))}
              </select>
            </div>
            <div className="two-columns">
              <ModelBreakdown
                ensemble={p.corners}
                market={cornerMarket}
                title="Modelos de córners"
              />
              <section className="panel">
                <h2>Líneas de córners</h2>
                <p className="subtle">
                  Local {num(p.corners.expected_home)} · Visitante{" "}
                  {num(p.corners.expected_away)} · Total{" "}
                  {num(p.corners.expected_total)}
                </p>
                <dl className="stat-list">
                  {MARKETS.filter((m) => m.endsWith("CORNERS")).map((m) => (
                    <div key={m}>
                      <dt>{marketName(m)}</dt>
                      <dd>{pct(p.corners.probabilities[m])}</dd>
                    </div>
                  ))}
                </dl>
                <Badge grade={p.corner_quality} />
                {p.corner_quality?.reasons?.map((r) => (
                  <p className="subtle" key={r}>
                    {r}
                  </p>
                ))}
              </section>
            </div>
          </div>
        </>
      )}
      {p && <LearnedPredictions prediction={p} />}
      {features?.external?.outcome_probabilities && (
        <section className="panel detail-section">
          <h2>Predicción externa · API-Football</h2>
          <dl className="stat-list">
            {Object.entries(features.external.outcome_probabilities).map(
              ([key, value]) => (
                <div key={key}>
                  <dt>{key}</dt>
                  <dd>{pct(value)}</dd>
                </div>
              ),
            )}
          </dl>
          <p className="subtle">{features.external.note}</p>
        </section>
      )}
      {odds.data && (
        <div className="detail-section">
          <OddsComparison comparisons={odds.data} />
        </div>
      )}
      {analysis.data && (
        <section className="panel detail-section analysis-panel">
          <div className="section-heading">
            <h2>Lectura del partido</h2>
            <span className="subtle">Explicación determinista · Español</span>
          </div>
          {analysis.data.paragraphs.map((p) => (
            <p key={p}>{p}</p>
          ))}
          <h3>Factores del análisis</h3>
          <div className="factors">
            {analysis.data.factors.map((factor, i) => (
              <div key={i} className={factor.direction}>
                <b>{factor.category}</b>
                <p>{factor.text}</p>
              </div>
            ))}
          </div>
        </section>
      )}
    </>
  );
}

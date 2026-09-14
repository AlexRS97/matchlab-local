import { useState } from "react";
import type { Features, Summary } from "../types";
import { ago, num, pct } from "../utils/format";

export function StatsPanel({
  features,
  home,
  away,
}: {
  features: Features;
  home: string;
  away: string;
}) {
  const [window, setWindow] = useState("10");
  return (
    <section className="panel">
      <div className="section-heading">
        <h2>Forma reciente</h2>
        <div className="segmented">
          {["5", "10", "20"].map((n) => (
            <button
              key={n}
              className={window === n ? "active" : ""}
              onClick={() => setWindow(n)}
            >
              Últimos {n}
            </button>
          ))}
        </div>
      </div>
      <div className="two-columns">
        <SummaryTable title={home} summary={features.home[window]} />
        <SummaryTable title={away} summary={features.away[window]} />
      </div>
      <h3 className="split-title">Casa / fuera · Muestras separadas</h3>
      <div className="two-columns">
        <SummaryTable title={`${home} en casa`} summary={features.home_split} />
        <SummaryTable title={`${away} fuera`} summary={features.away_split} />
      </div>
      <div className="two-columns recent-results">
        {[
          [home, features.recent_home],
          [away, features.recent_away],
        ].map(([name, matches]) => (
          <div key={String(name)}>
            <h3>{String(name)} · Resultados previos</h3>
            <div className="form-results">
              {(matches as Features["recent_home"])
                .slice(0, Number(window))
                .map((m) => (
                  <span
                    key={m.fixture_id}
                    className={
                      m.goals_for > m.goals_against
                        ? "win"
                        : m.goals_for === m.goals_against
                          ? "draw"
                          : "loss"
                    }
                    title={`${new Date(m.kickoff_utc).toLocaleDateString("es-ES")} · ${m.competition} · ${m.is_home ? "Casa" : "Fuera"}`}
                  >
                    {m.goals_for}–{m.goals_against}
                    <small>{m.is_home ? "C" : "F"}</small>
                  </span>
                ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
function SummaryTable({ title, summary }: { title: string; summary: Summary }) {
  return (
    <div>
      <h3>{title}</h3>
      <p className="subtle">
        Muestra: {summary.sample_size} · {summary.source} ·{" "}
        {ago(summary.last_updated)}
      </p>
      <dl className="stat-list">
        {[
          [
            "GF / GA",
            `${num(summary.goals_for)} / ${num(summary.goals_against)}`,
          ],
          ["Media total goles", num(summary.total_goals_average)],
          ["Over 2.5", pct(summary.over25_rate)],
          ["Ambos marcan", pct(summary.btts_rate)],
          [
            "Tiros / a puerta",
            `${num(summary.shots, 1)} / ${num(summary.shots_on_target, 1)}`,
          ],
          ["xG / xGA", `${num(summary.xg)} / ${num(summary.xga)}`],
          [
            "Córners a favor / contra",
            `${num(summary.corners_for)} / ${num(summary.corners_against)}`,
          ],
        ].map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

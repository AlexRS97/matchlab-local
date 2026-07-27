import Link from "next/link";
import { Fixture } from "@/lib/types";

const percent = (value: number) => `${Math.round(value * 100)}%`;
const selectionLabel: Record<string, string> = {
  Home: "Gana local",
  Draw: "Empate",
  Away: "Gana visitante",
  "Over 2.5": "Más de 2,5 goles",
  "Under 2.5": "Menos de 2,5 goles",
  "BTTS Yes": "Ambos marcan",
  "BTTS No": "No marcan ambos",
  "Over 8.5": "Más de 8,5 córners",
  "Under 8.5": "Menos de 8,5 córners",
  "Over 9.5": "Más de 9,5 córners",
  "Under 9.5": "Menos de 9,5 córners",
};

function TeamLogo({ name, url }: { name: string; url: string | null }) {
  return url ? <img src={url} alt="" className="team-logo" /> : <span className="team-fallback">{name[0]}</span>;
}

export function FixtureCard({ fixture }: { fixture: Fixture }) {
  const prediction = fixture.prediction;
  const recommendation = prediction?.recommendations[0];
  const kickoff = new Intl.DateTimeFormat("es-ES", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Madrid",
  }).format(new Date(fixture.kickoff_at));

  return (
    <Link href={`/partidos/${fixture.id}`} className="fixture-card">
      <div className="fixture-head">
        <span>{kickoff} · {fixture.round_name ?? "Próximo partido"}</span>
        {prediction && <span className={`quality ${prediction.data_quality}`}>Calidad {prediction.data_quality}</span>}
      </div>
      <div className="teams">
        <div className="team"><TeamLogo name={fixture.home_team.name} url={fixture.home_team.logo_url} /><span>{fixture.home_team.name}</span></div>
        <span className="versus">vs</span>
        <div className="team away"><span>{fixture.away_team.name}</span><TeamLogo name={fixture.away_team.name} url={fixture.away_team.logo_url} /></div>
      </div>
      {prediction ? (
        <>
          <div className="metric-grid">
            <div><small>Goles esperados</small><strong>{prediction.total_expected_goals.toFixed(2)}</strong><span>{prediction.home_expected_goals.toFixed(2)} — {prediction.away_expected_goals.toFixed(2)}</span></div>
            <div><small>Córners esperados</small><strong>{prediction.total_expected_corners?.toFixed(2) ?? "—"}</strong><span>{prediction.home_expected_corners?.toFixed(2) ?? "s/d"} — {prediction.away_expected_corners?.toFixed(2) ?? "s/d"}</span></div>
            <div><small>Más de 2,5</small><strong>{percent(prediction.over_2_5_probability)}</strong><span>Ambos marcan {percent(prediction.btts_probability)}</span></div>
          </div>
          {recommendation && (
            <div className={`recommendation-strip ${recommendation.kind}`}>
              <span>{recommendation.kind === "valor" ? "Valor detectado" : "Tendencia"}</span>
              <b>{selectionLabel[recommendation.selection] ?? recommendation.selection}</b>
              <strong>{percent(recommendation.probability)}</strong>
              {recommendation.decimal_odds && <em>@ {recommendation.decimal_odds.toFixed(2)}</em>}
            </div>
          )}
          <div className="probability-row">
            <span>1 <b>{percent(prediction.home_win_probability)}</b></span>
            <span>X <b>{percent(prediction.draw_probability)}</b></span>
            <span>2 <b>{percent(prediction.away_win_probability)}</b></span>
            <span className="confidence">Confianza {percent(prediction.confidence)}</span>
          </div>
        </>
      ) : <div className="no-analysis">Análisis pendiente por falta de datos.</div>}
    </Link>
  );
}

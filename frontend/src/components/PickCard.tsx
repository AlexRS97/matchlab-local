import { ArrowUpRight, Check, ChevronDown } from "lucide-react";
import { Link } from "react-router-dom";
import { BOOKMAKERS, type Pick } from "../types";
import { ago, ev, marketName, num, pct, time } from "../utils/format";
import { Badge } from "./Primitives";
export function PickCard({ pick }: { pick: Pick }) {
  const f = pick.fixture;
  const quote = pick.selected_quote;
  return (
    <article className="pick-card">
      <div className="pick-top">
        <span className="rank">#{pick.rank.toString().padStart(2, "0")}</span>
        <span>{f.league_name}</span>
        <time>{time(f.kickoff_utc)}</time>
      </div>
      <Link to={`/match/${f.fixture_id}`} className="pick-teams">
        {f.home_team}
        <span>vs</span>
        {f.away_team}
        <ArrowUpRight size={17} />
      </Link>
      <div className="market-label">{marketName(pick.market)}</div>
      <div className="pick-prob">
        <div>
          <small>PROBABILIDAD DEL MODELO</small>
          <strong>{pct(pick.probability)}</strong>
        </div>
        <Badge grade={pick.confidence} />
      </div>
      <div className="book-prices">
        {BOOKMAKERS.map((book) => {
          const q = pick.comparison.quotes[book];
          return (
            <div
              key={book}
              className={book === quote.bookmaker ? "best-price" : ""}
            >
              <small>{book}</small>
              <strong>
                {num(q?.decimal_odds)}
                {book === quote.bookmaker && <Check size={12} />}
              </strong>
              <span title={q?.timestamp}>
                {q
                  ? `${q.stale ? "STALE · " : ""}${q.is_manual ? "MANUAL · " : ""}${q.is_delayed ? "Delayed · " : ""}${ago(q.timestamp)}`
                  : "Sin cuota"}
              </span>
            </div>
          );
        })}
      </div>
      <div className="pick-metrics">
        <div>
          <small>CUOTA JUSTA</small>
          <b>{num(pick.comparison.fair_odds)}</b>
        </div>
        <div>
          <small>EDGE</small>
          <b className={(quote.edge ?? 0) > 0 ? "positive" : ""}>
            {pct(quote.edge, true)}
          </b>
        </div>
        <div>
          <small>EV</small>
          <b className={(quote.ev ?? 0) > 0 ? "positive" : ""}>
            {ev(quote.ev)}
          </b>
        </div>
      </div>
      <details className="pick-why">
        <summary>
          Por qué destaca <ChevronDown size={14} />
        </summary>
        <p>
          Probabilidad {pct(pick.probability)}, confianza{" "}
          {pick.confidence.score}/100 y calidad {pick.quality.score}/100, con{" "}
          {pick.quality.sample_size ?? "—"} partidos por equipo como mínimo.
        </p>
        <p>
          {quote.ev != null && quote.ev > 0
            ? "La cuota seleccionada supera la cuota justa del modelo."
            : "La posición refleja probabilidad; el precio puede no ofrecer valor positivo."}
        </p>
        {pick.quality.reasons?.map((r) => (
          <p key={r}>· {r}</p>
        ))}
      </details>
      <Link className="card-link" to={`/match/${f.fixture_id}`}>
        Ver análisis completo <ArrowUpRight size={14} />
      </Link>
    </article>
  );
}

import { BOOKMAKERS, type Comparison } from "../types";
import { ago, marketName, num, pct, ev } from "../utils/format";

export function OddsComparison({ comparisons }: { comparisons: Comparison[] }) {
  return (
    <section className="panel">
      <div className="section-heading">
        <h2>Comparación de cuotas</h2>
        <span className="subtle">Precios actuales · EV bruto</span>
      </div>
      <div className="table-scroll">
        <table className="detail-table">
          <thead>
            <tr>
              <th>Mercado</th>
              <th>Modelo / justa</th>
              {BOOKMAKERS.map((b) => (
                <th key={b}>{b}</th>
              ))}
              <th>Mejor</th>
              <th>Consenso mercado</th>
              <th>Edge</th>
              <th>EV</th>
            </tr>
          </thead>
          <tbody>
            {comparisons.map((c) => (
              <tr key={c.market}>
                <td>{marketName(c.market)}</td>
                <td>
                  {pct(c.model_probability)}
                  <small>{num(c.fair_odds)}</small>
                </td>
                {BOOKMAKERS.map((b) => {
                  const q = c.quotes[b];
                  return (
                    <td
                      key={b}
                      className={c.best_bookmaker === b ? "positive" : ""}
                    >
                      <strong>{num(q?.decimal_odds)}</strong>
                      <small>
                        {q
                          ? `${q.is_manual ? "MANUAL · " : ""}${q.is_delayed ? "Delayed · " : ""}${ago(q.timestamp)}`
                          : "Sin cuota"}
                      </small>
                      {q && (
                        <small title={q.timestamp}>
                          {q.stale ? "STALE · " : ""}
                          {q.source_label} · {q.devig_status}
                        </small>
                      )}
                      {q?.best_lay_price && (
                        <small>
                          Back {num(q.best_back_price)} / Lay{" "}
                          {num(q.best_lay_price)}
                        </small>
                      )}
                    </td>
                  );
                })}
                <td>
                  {num(c.best_odds)}
                  <small>{c.best_bookmaker ?? "—"}</small>
                </td>
                <td>
                  {pct(c.market_consensus)}
                  <small>{c.consensus_status}</small>
                </td>
                <td>{pct(c.best?.edge, true)}</td>
                <td>{ev(c.best?.ev)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

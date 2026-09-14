import { useState, type FormEvent } from "react";
import { api } from "../api/client";
import { BOOKMAKERS, MARKETS, type Fixture } from "../types";
import { marketName } from "../utils/format";
export function ManualOdds({
  fixtures,
  onSaved,
}: {
  fixtures: Fixture[];
  onSaved: () => void;
}) {
  const [fixture, setFixture] = useState("");
  const [book, setBook] = useState("BET365");
  const [market, setMarket] = useState("OVER_2_5_GOALS");
  const [odds, setOdds] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api("/odds/manual", {
        method: "POST",
        body: JSON.stringify({
          fixture_id: Number(fixture),
          bookmaker: book,
          market,
          line: market.startsWith("BTTS")
            ? null
            : Number(market.split("_")[1]) + 0.5,
          odds: Number(odds),
        }),
      });
      setMessage("Cuota manual guardada con fecha y origen.");
      onSaved();
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel manual-panel">
      <h2>Introducir cuota manual</h2>
      <p>
        Se guardará como MANUAL y tendrá la misma regla de caducidad que el
        resto de precios.
      </p>
      <form className="filter-main" onSubmit={submit}>
        <label>
          Partido
          <select
            required
            value={fixture}
            onChange={(e) => setFixture(e.target.value)}
          >
            <option value="">Selecciona un partido</option>
            {fixtures
              .filter(
                (f) =>
                  f.status === "NOT_STARTED" &&
                  new Date(f.kickoff_utc).getTime() > Date.now(),
              )
              .map((f) => (
                <option key={f.fixture_id} value={f.fixture_id}>
                  {f.home_team} — {f.away_team}
                </option>
              ))}
          </select>
        </label>
        <label>
          Casa
          <select value={book} onChange={(e) => setBook(e.target.value)}>
            {BOOKMAKERS.map((b) => (
              <option key={b}>{b}</option>
            ))}
          </select>
        </label>
        <label>
          Mercado
          <select value={market} onChange={(e) => setMarket(e.target.value)}>
            {MARKETS.map((m) => (
              <option key={m} value={m}>
                {marketName(m)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Cuota
          <input
            required
            type="number"
            min="1.01"
            step="0.01"
            value={odds}
            onChange={(e) => setOdds(e.target.value)}
          />
        </label>
        <button className="primary-button" disabled={busy}>
          Guardar
        </button>
      </form>
      {message && <p role="status">{message}</p>}
    </section>
  );
}

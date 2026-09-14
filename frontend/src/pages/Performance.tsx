import { useResource } from "../hooks/useResource";
import { Empty, ErrorMessage, Loading } from "../components/Primitives";
import { marketName, num, pct, ev } from "../utils/format";
interface Metric {
  market: string;
  number_predictions: number;
  settled_predictions: number;
  hit_rate: number | null;
  average_predicted_probability: number | null;
  hit_rate_interval: { low: number; high: number } | null;
  log_loss: number | null;
  brier_score: number | null;
  roi: number | null;
  priced_results: number;
}
export function Performance() {
  const { data, error, loading } = useResource<Metric[]>("/performance", 30000);
  return (
    <>
      <header className="page-header">
        <div>
          <div className="eyebrow">WORKSPACE / RESULTADOS</div>
          <h1>
            Performance<span>.</span>
          </h1>
          <p>Seguimiento de las predicciones publicadas antes del inicio.</p>
        </div>
      </header>
      <ErrorMessage message={error} />
      {loading && !data ? (
        <Loading />
      ) : data?.length ? (
        <section className="panel">
          <div className="table-scroll">
            <table className="detail-table">
              <thead>
                <tr>
                  {[
                    "Mercado",
                    "Predicciones",
                    "Resueltas",
                    "Frecuencia de acierto",
                    "Probabilidad media resueltas",
                    "Brier ↓",
                    "Log loss ↓",
                    "ROI bruto simulado",
                    "Resultados con cuota",
                  ].map((s) => (
                    <th key={s}>{s}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.map((m) => (
                  <tr key={m.market}>
                    <td>{marketName(m.market)}</td>
                    <td>{m.number_predictions}</td>
                    <td>{m.settled_predictions}</td>
                    <td>
                      {pct(m.hit_rate)}
                      {m.hit_rate_interval && (
                        <small>
                          IC 95%: {pct(m.hit_rate_interval.low)}–
                          {pct(m.hit_rate_interval.high)}
                        </small>
                      )}
                    </td>
                    <td>{pct(m.average_predicted_probability)}</td>
                    <td>{num(m.brier_score, 4)}</td>
                    <td>{num(m.log_loss, 4)}</td>
                    <td>{ev(m.roi)}</td>
                    <td>{m.priced_results}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : (
        <Empty
          title="Aún no hay predicciones registradas"
          text="Se guardará la primera predicción de cada partido y mercado. Los resultados se incorporan al actualizar los partidos finalizados."
        />
      )}
      <section className="panel detail-section">
        <h2>Cómo leer los resultados</h2>
        <p className="subtle">
          Brier mide el error de probabilidad: cuanto menor, mejor. La
          frecuencia de acierto refleja cuántas veces ocurre el mercado, sin
          aplicar un umbral de selección. La probabilidad media usa esos mismos
          partidos resueltos. El intervalo de Wilson refleja la incertidumbre
          binomial aproximada de la frecuencia, y puede ser amplio con pocas
          observaciones.
        </p>
        <p className="subtle">
          El ROI simula una unidad por cada pronóstico registrado con cuota
          disponible. No representa apuestas ejecutadas ni una cartera filtrada
          de Top Picks. Excluye comisiones; los partidos sin resultado o sin
          cuota no entran en ese cálculo.
        </p>
        <p className="subtle">
          El laboratorio de modelos muestra una evaluación histórica
          independiente. Esta pantalla acumula seguimiento prospectivo desde el
          uso de la aplicación.
        </p>
      </section>
    </>
  );
}

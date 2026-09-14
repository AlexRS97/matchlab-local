import { Link } from "react-router-dom";
import { MARKETS, type Prediction } from "../types";
import { marketName, pct, ago } from "../utils/format";
export function LearnedPredictions({ prediction }: { prediction: Prediction }) {
  const learned = prediction.learning;
  return (
    <section className="panel detail-section">
      <div className="section-heading">
        <h2>Machine learning y deep learning</h2>
        <Link className="back-link" to="/learning">
          Ver evaluación de modelos →
        </Link>
      </div>
      {learned?.status === "available" ? (
        <>
          <p className="subtle">
            Versión {learned.run_id?.slice(0, 12)} · entrenada{" "}
            {ago(learned.trained_at)}. Las siguientes probabilidades se muestran
            separadas por modelo.
          </p>
          <div className="table-scroll">
            <table className="detail-table">
              <thead>
                <tr>
                  <th>Mercado</th>
                  <th>Estadístico</th>
                  {Object.keys(learned.models).map((n) => (
                    <th key={n}>{n.toUpperCase()}</th>
                  ))}
                  <th>Final</th>
                </tr>
              </thead>
              <tbody>
                {MARKETS.map((m) => (
                  <tr key={m}>
                    <td>{marketName(m)}</td>
                    <td>
                      {pct(
                        prediction.statistical_probabilities?.[
                          m.endsWith("CORNERS") ? "corners" : "goals"
                        ][m],
                      )}
                    </td>
                    {Object.entries(learned.models).map(([n, p]) => (
                      <td key={n}>{pct(p[m])}</td>
                    ))}
                    <td>
                      {pct(
                        (m.endsWith("CORNERS")
                          ? prediction.corners
                          : prediction.goals
                        ).probabilities[m],
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="learning-note">
            La probabilidad final incorpora únicamente el modelo promovido de
            cada grupo, hasta un 20%. Los goles esperados y la matriz de
            marcadores describen el motor estadístico.
          </p>
        </>
      ) : (
        <p className="subtle">
          {learned?.reason ??
            "No hay un modelo entrenado disponible para este partido."}
        </p>
      )}
    </section>
  );
}

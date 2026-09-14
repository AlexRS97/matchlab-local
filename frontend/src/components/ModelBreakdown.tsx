import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Ensemble } from "../types";
import { modelName, num, pct } from "../utils/format";

export function ModelBreakdown({
  ensemble,
  market,
  title,
}: {
  ensemble: Ensemble;
  market: string;
  title: string;
}) {
  const consensus = ensemble.consensus[market];
  const chart = ensemble.models
    .filter((m) => m.probabilities[market] != null)
    .map((m) => ({
      name: modelName(m.name),
      probability: Math.round(m.probabilities[market] * 1000) / 10,
    }));
  return (
    <section className="panel">
      <div className="section-heading">
        <h2>{title}</h2>
        <span className="subtle">Modelos y ensemble</span>
      </div>
      <div className="model-list">
        {ensemble.models.map((m) => (
          <div key={m.name}>
            <span>{modelName(m.name)}</span>
            <strong>{pct(m.probabilities[market])}</strong>
            <small>
              {m.status === "available"
                ? `Peso efectivo: ${pct(ensemble.weights?.[market]?.[m.name])}`
                : m.reason}
            </small>
          </div>
        ))}
      </div>
      <div className="ensemble-total">
        <span>ENSEMBLE</span>
        <strong>{pct(ensemble.probabilities[market])}</strong>
      </div>
      {consensus && (
        <p className="subtle">
          Desacuerdo {consensus.model_disagreement} · Desviación{" "}
          {num(consensus.model_std * 100, 1)} pp · Rango{" "}
          {pct(consensus.model_min)}–{pct(consensus.model_max)}
        </p>
      )}
      {chart.length > 0 && (
        <div className="chart-box">
          <ResponsiveContainer width="100%" height={200}>
            <BarChart
              data={chart}
              margin={{ left: -20, right: 10, top: 20, bottom: 15 }}
            >
              <CartesianGrid stroke="#253142" vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 9, fill: "#9cabc0" }}
                axisLine={false}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fontSize: 9, fill: "#9cabc0" }}
                unit="%"
                axisLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: "#131d2a",
                  border: "1px solid #35465c",
                  fontSize: 11,
                }}
              />
              <Bar
                dataKey="probability"
                name="Probabilidad %"
                fill="#c6f66b"
                radius={[4, 4, 0, 0]}
                maxBarSize={45}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}

import { useState } from "react";
import { BrainCircuit, Download, Play, ArrowUpRight } from "lucide-react";
import { useResource } from "../hooks/useResource";
import { api } from "../api/client";
import { Empty, ErrorMessage, Loading } from "../components/Primitives";
import { num, ago, marketName, pct } from "../utils/format";
interface Metrics {
  goals: number | null;
  corners: number | null;
  markets: Record<
    string,
    {
      samples: number;
      brier: number;
      log_loss: number;
      ece: number;
      mean_probability: number;
      observed_rate: number;
    }
  >;
}
interface Report {
  league_statistics?: Record<
    string,
    Record<
      string,
      {
        family: string;
        gate: { promoted: boolean; samples?: number };
        validation_samples: number;
      }
    >
  >;
  league_champions?: Record<
    string,
    Record<
      string,
      { family: string; gate: { promoted: boolean; samples?: number } }
    >
  >;
  run_id: string;
  created_at: string;
  duration_seconds: number;
  dataset: {
    rows: number;
    historical_matches: number;
    first_date: string;
    last_date: string;
  };
  splits: Record<string, { samples: number; from: string; to: string }>;
  baseline: Metrics;
  models: Record<
    string,
    {
      status: string;
      error?: string;
      validation: Metrics;
      test: Metrics;
      epochs: number | null;
    }
  >;
  champions: Record<
    string,
    {
      family: string;
      blend_weight: number;
      blended_test: number;
      gate: {
        promoted: boolean;
        mean: number;
        ci_lower: number;
        ci_upper: number;
        samples: number;
      };
    }
  >;
  limitations: string[];
}
interface State {
  data_health?: {
    coverage: {
      league_code: string;
      matches: number;
      first_match: string;
      latest_match: string;
    }[];
    new_matches: number;
    model_age_days: number | null;
    training_recommended: boolean;
    provenance_available: boolean;
  };
  historical_matches: number;
  config: {
    threads?: number;
    automatic_training: boolean;
    daily_update_hour: number;
    retrain_days: number;
    minimum_new_samples: number;
  };
  job: { running: boolean; phase: string; errors: string[] };
  last_update: {
    timestamp: string;
    downloaded_files: number;
    errors: string[];
  } | null;
  report: Report | null;
}
export function Learning() {
  const resource = useResource<State>("/learning/status", 5000);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState("");
  const data = resource.data;
  const report = data?.report;
  async function action(path: string) {
    setBusy(true);
    setError("");
    try {
      await api(`/learning/${path}`, { method: "POST" });
      resource.reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo iniciar");
    } finally {
      setBusy(false);
    }
  }
  const names = report
    ? Object.keys(report.models).filter(
        (k) => report.models[k].status === "trained",
      )
    : [];
  const active = names.includes(selected) ? selected : names[0];
  const metrics = report?.models[active]?.test;
  return (
    <>
      <header className="page-header">
        <div>
          <div className="eyebrow">WORKSPACE / MACHINE LEARNING</div>
          <h1>
            Model lab<span>.</span>
          </h1>
          <p>Modelos comparados con partidos posteriores al entrenamiento.</p>
        </div>
        <div className="header-actions">
          <button
            className="secondary-button"
            disabled={busy || data?.job.running}
            onClick={() => action("update")}
          >
            <Download size={14} />
            Actualizar datos
          </button>
          <button
            className="primary-button"
            disabled={busy || data?.job.running}
            onClick={() => action("train")}
          >
            <Play size={14} />
            Entrenar modelos
          </button>
        </div>
      </header>
      <ErrorMessage message={error || resource.error} />
      {data?.job.running && (
        <div className="notice">
          <BrainCircuit size={17} />
          <span>{data.job.phase}</span>
        </div>
      )}
      {data?.job.errors.map((e) => (
        <ErrorMessage key={e} message={e} />
      ))}
      {resource.loading && !data && <Loading />}
      <div className="stats-grid">
        <div className="stat-card">
          <span>Partidos históricos</span>
          <strong>
            {data?.historical_matches.toLocaleString("es-ES") ?? "—"}
          </strong>
          <small>Resultados reales / 5 ligas</small>
        </div>
        <div className="stat-card">
          <span>Muestras con historial</span>
          <strong>{report?.dataset.rows.toLocaleString("es-ES") ?? "—"}</strong>
          <small>Al menos 5 partidos por equipo</small>
        </div>
        <div className="stat-card">
          <span>Modelos entrenados</span>
          <strong>
            {names.length} <small>/ 5</small>
          </strong>
          <small>3 modelos de árboles + 2 redes</small>
        </div>
        <div className="stat-card">
          <span>Actualización diaria</span>
          <strong>
            {String(data?.config.daily_update_hour ?? 6).padStart(2, "0")}:00
          </strong>
          <small>
            Con la app abierta · {ago(data?.last_update?.timestamp)}
          </small>
        </div>
        <div className="stat-card">
          <span>Último entrenamiento</span>
          <strong className="small-value">{ago(report?.created_at)}</strong>
          <small>
            {data?.config.automatic_training
              ? "Entrenamiento automático activado"
              : "Manual · pulsa Entrenar modelos"}
          </small>
        </div>
      </div>
      {data?.data_health && (
        <section className="panel detail-section">
          <div className="section-heading">
            <h2>Estado de los datos y modelos</h2>
            <span className="subtle">
              {data.config.automatic_training
                ? "Revisión automática al abrir"
                : "Entrenamiento manual"}{" "}
              · {data.config.threads ?? "CPU"} hilos disponibles
            </span>
          </div>
          <p className="subtle">
            {data.data_health.new_matches} partidos nuevos desde el último
            entrenamiento.
            {data.data_health.model_age_days != null
              ? ` Modelo de hace ${data.data_health.model_age_days} días.`
              : " Todavía no hay un modelo publicado."}{" "}
            {data.data_health.training_recommended
              ? data.config.automatic_training
                ? "Los modelos se actualizarán al revisar el histórico."
                : "Conviene revisar los datos y entrenar cuando puedas dedicarle recursos."
              : "Puedes seguir usando los modelos guardados."}
          </p>
          <div className="table-scroll">
            <table className="detail-table">
              <thead>
                <tr>
                  <th>Liga</th>
                  <th>Partidos históricos</th>
                  <th>Primera fecha</th>
                  <th>Último resultado disponible</th>
                </tr>
              </thead>
              <tbody>
                {data.data_health.coverage.map((row) => (
                  <tr key={row.league_code}>
                    <td>
                      {(
                        {
                          E0: "Premier League",
                          D1: "Bundesliga",
                          SP1: "La Liga",
                          I1: "Serie A",
                          F1: "Ligue 1",
                        } as Record<string, string>
                      )[row.league_code] ?? row.league_code}
                    </td>
                    <td>{row.matches.toLocaleString("es-ES")}</td>
                    <td>{row.first_match}</td>
                    <td>{row.latest_match}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="learning-note">
            La fecha del último resultado indica la cobertura del proveedor; una
            descarga reciente puede contener datos anteriores. Los próximos
            entrenamientos guardan la huella de los datos, el código y las
            versiones de las bibliotecas para poder reproducirlos.
          </p>
        </section>
      )}
      {!report && (
        <Empty
          title="Laboratorio listo para entrenar"
          text="Descarga el histórico y entrena para comparar CatBoost, LightGBM, XGBoost, MLP y GRU con el ensemble estadístico."
        />
      )}
      {report && (
        <>
          {report.league_statistics &&
            Object.keys(report.league_statistics).length > 0 && (
              <section className="panel detail-section">
                <h2>Modelos por liga</h2>
                <p className="subtle">
                  Goles y córners se comparan por separado. La selección usa
                  validación temporal y solo se activa tras superar su control
                  de mejora; una muestra insuficiente conserva la referencia.
                </p>
                <div className="table-scroll">
                  <table className="detail-table">
                    <thead>
                      <tr>
                        <th>Liga</th>
                        <th>Mercados</th>
                        <th>Modelo estadístico activo</th>
                        <th>Candidato ML</th>
                        <th>Estado ML / muestra de test</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(report.league_statistics).flatMap(
                        ([league, groups]) =>
                          Object.entries(groups).map(([group, selection]) => {
                            const ml =
                              report.league_champions?.[league]?.[group];
                            return (
                              <tr key={`${league}-${group}`}>
                                <td>
                                  {(
                                    {
                                      "39": "Premier League",
                                      "78": "Bundesliga",
                                      "140": "La Liga",
                                      "135": "Serie A",
                                      "61": "Ligue 1",
                                    } as Record<string, string>
                                  )[league] ?? league}
                                </td>
                                <td>
                                  {group === "goals"
                                    ? "Goles / BTTS"
                                    : "Córners"}
                                </td>
                                <td>
                                  {selection.gate.promoted
                                    ? selection.family
                                    : "Ensemble general"}
                                </td>
                                <td>
                                  {ml?.family.toUpperCase() ??
                                    "Referencia general"}
                                </td>
                                <td>
                                  {ml
                                    ? `${ml.gate.promoted ? "Activo al 20%" : "Sin mejora confirmada"} · ${ml.gate.samples ?? 0} partidos`
                                    : "Sin muestra suficiente"}
                                </td>
                              </tr>
                            );
                          }),
                      )}
                    </tbody>
                  </table>
                </div>
                <p className="learning-note">
                  No existe un ganador permanente. La comparación se renueva al
                  actualizar los modelos con nuevos datos; intervalos por semanas
                  ajustados por el número de ligas y grupos comparados.
                </p>
              </section>
            )}
          <div className="two-columns detail-section">
            {Object.entries(report.champions).map(([group, c]) => (
              <section className="panel" key={group}>
                <div className="section-heading">
                  <h2>
                    {group === "goals" ? "Goles y ambos marcan" : "Córners"}
                  </h2>
                  <span
                    className={`badge ${c.gate.promoted ? "grade-good" : "grade-low"}`}
                  >
                    {c.gate.promoted ? "REFERENCIA VALIDADA" : "EN OBSERVACIÓN"}
                  </span>
                </div>
                <h3>{c.family.toUpperCase()} · seleccionado en validación</h3>
                <dl className="stat-list">
                  <div>
                    <dt>Brier estadístico / mezcla</dt>
                    <dd>
                      {num(report.baseline[group as "goals" | "corners"], 4)} /{" "}
                      {num(c.blended_test, 4)}
                    </dd>
                  </div>
                  <div>
                    <dt>Mejora media de Brier</dt>
                    <dd>{num(c.gate.mean, 5)}</dd>
                  </div>
                  <div>
                    <dt>Intervalo bootstrap del 95%</dt>
                    <dd>
                      {num(c.gate.ci_lower, 5)} a {num(c.gate.ci_upper, 5)}
                    </dd>
                  </div>
                  <div>
                    <dt>Peso de la referencia general</dt>
                    <dd>{c.gate.promoted ? pct(c.blend_weight) : "0%"}</dd>
                  </div>
                </dl>
                <p className="subtle">
                  {c.gate.promoted
                    ? "La mezcla general pasó la comparación temporal. La tabla por liga determina si tiene un candidato propio habilitado."
                    : "El sistema conserva el cálculo estadístico hasta obtener evidencia de mejora."}
                </p>
              </section>
            ))}
          </div>
          <section className="panel detail-section">
            <h2>Comparación en el periodo de prueba</h2>
            <p className="subtle">
              Brier menor es mejor. El ganador se elige en validación; la
              calibración usa otro bloque temporal.
            </p>
            <div className="table-scroll">
              <table className="detail-table">
                <thead>
                  <tr>
                    {[
                      "Modelo",
                      "Tipo",
                      "Goles · validación",
                      "Goles · test",
                      "Córners · validación",
                      "Córners · test",
                      "Estado",
                    ].map((v) => (
                      <th key={v}>{v}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Ensemble estadístico</td>
                    <td>Poisson / DC / NB / forma</td>
                    <td>—</td>
                    <td>{num(report.baseline.goals, 4)}</td>
                    <td>—</td>
                    <td>{num(report.baseline.corners, 4)}</td>
                    <td>Referencia</td>
                  </tr>
                  {Object.entries(report.models).map(([name, m]) => (
                    <tr key={name}>
                      <td>{name.toUpperCase()}</td>
                      <td>
                        {name === "gru"
                          ? "Red recurrente"
                          : name === "mlp"
                            ? "Red densa"
                            : "Gradient boosting"}
                      </td>
                      <td>{num(m.validation?.goals, 4)}</td>
                      <td>{num(m.test?.goals, 4)}</td>
                      <td>{num(m.validation?.corners, 4)}</td>
                      <td>{num(m.test?.corners, 4)}</td>
                      <td title={m.error}>
                        {m.status === "trained" ? "Entrenado" : m.error}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="panel detail-section">
            <div className="section-heading">
              <h2>Calibración por mercado</h2>
              <select
                aria-label="Modelo para métricas"
                value={active}
                onChange={(e) => setSelected(e.target.value)}
              >
                {names.map((n) => (
                  <option key={n} value={n}>
                    {n.toUpperCase()}
                  </option>
                ))}
              </select>
            </div>
            <div className="table-scroll">
              <table className="detail-table">
                <thead>
                  <tr>
                    {[
                      "Mercado",
                      "Muestra",
                      "Brier ↓",
                      "Log loss ↓",
                      "ECE ↓",
                      "P media",
                      "Frecuencia real",
                    ].map((v) => (
                      <th key={v}>{v}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(metrics?.markets ?? {}).map(([market, m]) => (
                    <tr key={market}>
                      <td>{marketName(market)}</td>
                      <td>{m.samples}</td>
                      <td>{num(m.brier, 4)}</td>
                      <td>{num(m.log_loss, 4)}</td>
                      <td>{pct(m.ece)}</td>
                      <td>{pct(m.mean_probability)}</td>
                      <td>{pct(m.observed_rate)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="panel detail-section">
            <h2>Separación temporal</h2>
            <div className="split-timeline">
              {Object.entries(report.splits).map(([key, s]) => (
                <div key={key}>
                  <b>
                    {
                      {
                        train: "Entrenamiento",
                        validation: "Validación",
                        calibration: "Calibración",
                        test: "Prueba final",
                      }[key]
                    }
                  </b>
                  <strong>{s.samples.toLocaleString("es-ES")}</strong>
                  <small>
                    {s.from.slice(0, 10)} → {s.to.slice(0, 10)}
                  </small>
                </div>
              ))}
            </div>
            <p className="subtle">
              Se excluyen dos días entre bloques. Imputación y normalización se
              ajustan únicamente con entrenamiento. Las cuotas y el resultado
              del partido objetivo no son entradas del modelo.
            </p>
          </section>
        </>
      )}
      <section className="panel detail-section">
        <h2>Datos, actualización y alcance</h2>
        <p className="subtle">
          El histórico se comprueba cada día a las{" "}
          {data?.config.daily_update_hour ?? 6}:00 mientras el backend está en
          marcha, con recuperación al siguiente arranque. Football-Data publica
          a su propio ritmo; consultar cada día no implica datos nuevos cada
          día.
        </p>
        <p className="subtle">
          {data?.config.automatic_training
            ? "Los modelos se revisan al abrir. Se reentrenan si cambia el histórico o están caducados; si siguen vigentes, se reutilizan. Con la aplicación cerrada no se ejecutan trabajos."
            : "Entrenamiento manual: los modelos solo se vuelven a entrenar al pulsar Entrenar modelos."}{" "}
          Se conservan versiones, métricas y artefactos para reproducir la
          inferencia.
        </p>
        {report?.limitations.map((v) => (
          <p className="subtle" key={v}>
            {v}
          </p>
        ))}
        <a
          className="back-link"
          href="https://football-data.co.uk/data.php"
          target="_blank"
          rel="noreferrer"
        >
          Football-Data · fuente del histórico <ArrowUpRight size={13} />
        </a>
      </section>
    </>
  );
}

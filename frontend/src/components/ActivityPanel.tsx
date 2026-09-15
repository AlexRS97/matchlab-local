import { Activity, Check, ChevronDown, TriangleAlert } from "lucide-react";
import { useEffect } from "react";
import { useResource } from "../hooks/useResource";

interface Step {
  key: string;
  label: string;
  status: "pending" | "running" | "complete" | "warning" | "failed";
  fraction: number;
}
interface Job {
  running: boolean;
  kind?: "fixtures" | "history" | "training" | "odds";
  status?: string;
  errors: string[];
  started_at?: string;
  finished_at?: string;
  progress?: {
    percent: number;
    stage: string;
    detail: string;
    indeterminate: boolean;
    steps: Step[];
  };
}
interface ActivityStatus {
  job: Job;
  learning: Job;
  odds?: Job;
}

function duration(job: Job) {
  if (!job.started_at) return "";
  const end = job.running
    ? Date.now()
    : Date.parse(job.finished_at ?? job.started_at);
  const seconds = Math.max(
    0,
    Math.floor((end - Date.parse(job.started_at)) / 1000),
  );
  return seconds < 60
    ? `${seconds} s`
    : `${Math.floor(seconds / 60)} min ${seconds % 60} s`;
}

function JobCard({ job, label }: { job: Job; label: string }) {
  const progress = job.progress;
  if (!progress) return null;
  const warning =
    job.errors.length > 0 ||
    job.status === "partial" ||
    job.status === "failed";
  const percent = progress.percent;
  const complete = !job.running && job.status === "complete";
  const state = job.running
    ? "En curso"
    : complete
      ? "Completado"
      : job.status === "partial"
        ? "Terminado con avisos"
        : "Interrumpido";
  return (
    <article className={`activity-card ${warning ? "has-warning" : ""}`}>
      <div className="activity-card-heading">
        <strong>{label}</strong>
        <span>
          {job.running ? (
            <Activity size={13} />
          ) : warning ? (
            <TriangleAlert size={13} />
          ) : (
            <Check size={13} />
          )}
          {state}
        </span>
      </div>
      <div className="activity-percent">
        <b>
          {percent.toLocaleString("es-ES", { maximumFractionDigits: 1 })}
          <small> %</small>
        </b>
        <span>
          {job.running
            ? `${(100 - percent).toLocaleString("es-ES", { maximumFractionDigits: 1 })} % por completar`
            : warning
              ? "Revisa los avisos antes de usar los datos"
              : "Trabajo finalizado"}
        </span>
      </div>
      <div
        className={`activity-track ${job.running && progress.indeterminate ? "is-waiting" : ""}`}
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        aria-valuetext={`${percent} %. ${state}. ${progress.stage}`}
      >
        <i style={{ width: `${percent}%` }} />
      </div>
      <div className="activity-phase">
        <strong>{progress.stage}</strong>
        <time>{duration(job)}</time>
      </div>
      <p className="activity-detail">
        {progress.detail ||
          (job.running ? "Preparando esta fase…" : "Revisión completada")}
      </p>
      <details className="activity-steps">
        <summary>
          <ChevronDown size={13} /> Ver fases ·{" "}
          {
            progress.steps.filter((s) =>
              ["complete", "warning"].includes(s.status),
            ).length
          }
          /{progress.steps.length}
        </summary>
        <ol>
          {progress.steps.map((step) => (
            <li key={step.key} data-state={step.status}>
              <span>{step.label}</span>
              <b>
                {step.status === "pending"
                  ? "Pendiente"
                  : step.status === "warning"
                    ? "Con avisos"
                    : step.status === "failed"
                      ? "Error"
                      : `${Math.round(step.fraction * 100)} %`}
              </b>
            </li>
          ))}
        </ol>
      </details>
      {job.errors.length > 0 && (
        <details className="activity-errors">
          <summary>
            {job.errors.length} aviso{job.errors.length !== 1 ? "s" : ""} · ver
            detalle
          </summary>
          <ul>
            {Array.from(new Set(job.errors)).map((error) => (
              <li key={error}>{error}</li>
            ))}
          </ul>
        </details>
      )}
    </article>
  );
}

export function ActivityPanel() {
  const { data, error } = useResource<ActivityStatus>("/refresh/status", 1500);
  const jobs = [data?.job, data?.learning, data?.odds].filter(
    (job): job is Job => !!job?.progress,
  );
  const finished =
    !error &&
    jobs.length > 0 &&
    jobs.every((job) => !job.running && !!job.status);
  const failed = jobs.some((job) =>
    ["failed", "cancelled"].includes(job.status ?? ""),
  );
  const warnings = jobs.some(
    (job) => job.errors.length > 0 || job.status === "partial",
  );
  const phases = jobs.reduce((sum, job) => sum + job.progress!.steps.length, 0);
  const completed = jobs.reduce(
    (sum, job) => sum + job.progress!.percent * job.progress!.steps.length,
    0,
  );
  const percent = Math.min(
    finished && !failed ? 100 : 99.9,
    completed / Math.max(1, phases),
  );
  useEffect(() => {
    const original = document.title;
    if (finished)
      document.title =
        failed || warnings
          ? "Revisa los avisos · MatchLab"
          : "Actualización terminada · MatchLab";
    return () => {
      document.title = original;
    };
  }, [finished, failed, warnings]);
  if (!data && !error)
    return (
      <div className="activity-connecting" role="status">
        Conectando con MatchLab y consultando los trabajos…
      </div>
    );
  const hasJobs =
    data?.job.progress || data?.learning.progress || data?.odds?.progress;
  if (!hasJobs && !error) return null;
  return (
    <section className="activity-panel" aria-label="Progreso de los trabajos">
      <div className="activity-heading">
        <span>
          <Activity size={15} /> Actividad de MatchLab
        </span>
        <small>Avance por fases · el tiempo de cada fase puede variar</small>
      </div>
      {jobs.length > 0 && (
        <div className="activity-overall">
          <div className="activity-card-heading">
            <strong>
              {finished
                ? "Revisión finalizada"
                : "Preparando datos, modelos y análisis"}
            </strong>
            <b>
              {percent.toLocaleString("es-ES", { maximumFractionDigits: 1 })} %
            </b>
          </div>
          <div
            className="activity-track"
            role="progressbar"
            aria-label="Progreso total"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Number(percent.toFixed(1))}
          >
            <i style={{ width: `${percent}%` }} />
          </div>
        </div>
      )}
      {finished && (
        <div
          className={`activity-completion ${failed || warnings ? "has-warning" : ""}`}
          role="status"
          aria-live="polite"
        >
          {failed || warnings ? (
            <TriangleAlert size={20} />
          ) : (
            <Check size={20} />
          )}
          <div>
            <strong>
              {failed
                ? "La actualización se ha interrumpido"
                : warnings
                  ? "Actualización finalizada con avisos"
                  : "MatchLab está preparado"}
            </strong>
            <p>
              {failed || warnings
                ? "Revisa los avisos de las fuentes y los trabajos antes de utilizar los resultados."
                : "Datos, revisión de modelos y análisis terminados. Ya puedes consultar los resultados."}
            </p>
          </div>
        </div>
      )}
      {error && (
        <p className="activity-disconnected" role="status">
          Sin conexión con el backend. El progreso mostrado puede estar
          desactualizado. Abre MatchLab para continuar.
        </p>
      )}
      <div className="activity-grid">
        {data && (
          <>
            <JobCard job={data.job} label="Partidos, análisis y cuotas" />
            <JobCard
              job={data.learning}
              label={
                data.learning.kind === "training"
                  ? "Entrenamiento de modelos"
                  : "Actualización del histórico"
              }
            />
          </>
        )}
        {data?.odds?.progress && (
          <JobCard job={data.odds} label="Actualización periódica de cuotas" />
        )}
      </div>
    </section>
  );
}

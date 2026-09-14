import { AlertCircle, LoaderCircle } from "lucide-react";
import type { Grade } from "../types";
export function Badge({ grade }: { grade?: Grade | null }) {
  return (
    <span
      className={`badge grade-${grade?.category.toLowerCase() ?? "insufficient"}`}
      title={grade ? `${grade.score}/100` : "Sin datos"}
    >
      {grade?.category.replaceAll("_", " ") ?? "INSUFFICIENT"}
      {grade && <small>{grade.score.toFixed(0)}</small>}
    </span>
  );
}
export function ErrorMessage({ message }: { message: string }) {
  return message ? (
    <div className="notice error" role="alert">
      <AlertCircle size={16} />
      <span>{message}</span>
    </div>
  ) : null;
}
export function Loading() {
  return (
    <div className="empty">
      <LoaderCircle className="spin" size={24} />
      <p>Cargando datos…</p>
    </div>
  );
}
export function Empty({ title, text }: { title: string; text: string }) {
  return (
    <div className="empty">
      <div className="empty-icon">∅</div>
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

import Link from "next/link";

export default function NotFound() {
  return (
    <main className="shell state-shell">
      <div className="state-illustration" aria-hidden="true">404</div>
      <p className="eyebrow">FUERA DE JUEGO</p>
      <h1>Esta página no existe.</h1>
      <p>Puede que el partido ya no esté disponible o que el enlace sea incorrecto.</p>
      <div className="state-actions">
        <Link href="/#partidos">Ver próximos partidos</Link>
      </div>
    </main>
  );
}

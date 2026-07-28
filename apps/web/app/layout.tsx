import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "MatchLab — Análisis de fútbol",
  description: "Predicciones probabilísticas de goles y córners con trazabilidad de datos.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es">
      <body>
        <header className="topbar">
          <Link href="/" className="brand">
            <img src="/mark.svg" alt="" width="40" height="40" />
            <span className="brand-copy">
              <b>MatchLab</b>
              <small>Football intelligence</small>
            </span>
          </Link>
          <nav className="top-actions" aria-label="Navegación principal">
            <Link href="/#resumen" className="top-link">Resumen</Link>
            <Link href="/#partidos" className="top-link">Partidos</Link>
            <div className="model-pill"><span /> Modelo activo</div>
          </nav>
        </header>
        {children}
        <footer>
          <div>
            <strong>MatchLab</strong>
            <span>Análisis probabilístico para tomar decisiones mejor informadas.</span>
          </div>
          <p>Las probabilidades no son certezas. Valida el modelo y apuesta siempre con responsabilidad.</p>
        </footer>
      </body>
    </html>
  );
}

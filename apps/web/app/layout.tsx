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
            <img src="/mark.svg" alt="" width="38" height="38" />
            <span>MatchLab</span>
          </Link>
          <div className="model-pill"><span /> Modelo probabilístico · análisis avanzado</div>
        </header>
        {children}
        <footer>
          <strong>MatchLab</strong> estima probabilidades, no certezas. Valida el modelo antes de
          arriesgar dinero y apuesta siempre con responsabilidad.
        </footer>
      </body>
    </html>
  );
}

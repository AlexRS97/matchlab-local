import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import {
  Activity,
  CalendarDays,
  ChartNoAxesCombined,
  CircleDot,
  Flag,
  Layers,
  Settings as SettingsIcon,
  ArrowUpRight,
} from "lucide-react";
import { Today } from "./pages/Today";
import { ActivityPanel } from "./components/ActivityPanel";
const MatchDetail = React.lazy(() =>
  import("./pages/MatchDetail").then((m) => ({ default: m.MatchDetail })),
);
const SettingsPage = React.lazy(() =>
  import("./pages/Settings").then((m) => ({ default: m.Settings })),
);
const Learning = React.lazy(() =>
  import("./pages/Learning").then((m) => ({ default: m.Learning })),
);
const Performance = React.lazy(() =>
  import("./pages/Performance").then((m) => ({ default: m.Performance })),
);
import { Loading, Empty } from "./components/Primitives";
import "./styles.css";
function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <aside className="sidebar">
          <NavLink to="/" className="brand">
            <span className="brand-icon">
              <Activity size={22} />
            </span>
            <span>
              matchlab<small>FOOTBALL ANALYTICS AI</small>
            </span>
          </NavLink>
          <div className="nav-label">WORKSPACE</div>
          <nav>
            {[
              ["/", "TODAY", CalendarDays],
              ["/top", "TOP PICKS", ChartNoAxesCombined],
              ["/goals", "GOALS", CircleDot],
              ["/corners", "CORNERS", Flag],
              ["/odds", "ODDS", Layers],
              ["/learning", "MODEL LAB", Activity],
              ["/performance", "PERFORMANCE", ChartNoAxesCombined],
              ["/settings", "SETTINGS", SettingsIcon],
            ].map(([path, label, Icon]) => {
              const I = Icon as typeof Activity;
              return (
                <NavLink end to={String(path)} key={String(path)}>
                  <I size={17} />
                  {String(label)}
                  <span className="nav-active-dot" />
                </NavLink>
              );
            })}
          </nav>
          <div className="sidebar-bottom">
            <NavLink to="/settings">
              <SettingsIcon size={17} /> SETTINGS
            </NavLink>
            <div className="local-status">
              <i />
              <div>
                Ejecucion local<small>Solo analisis · Prepartido</small>
              </div>
              <ArrowUpRight size={13} />
            </div>
            <span className="version">MATCHLAB / V1.0</span>
          </div>
        </aside>
        <main className="main-content">
          <ActivityPanel />
          <React.Suspense fallback={<Loading />}>
            <Routes>
              <Route path="/learning" element={<Learning />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/performance" element={<Performance />} />
              <Route
                path="*"
                element={
                  <Empty
                    title="Pagina no encontrada"
                    text="Selecciona una vista en la navegacion."
                  />
                }
              />
              <Route path="/match/:id" element={<MatchDetail />} />
              {["/", "/top", "/goals", "/corners", "/odds"].map((path) => (
                <Route path={path} element={<Today />} key={path} />
              ))}
            </Routes>
          </React.Suspense>
          <footer>
            MatchLab · Modelos estadisticos independientes de las cuotas{" "}
            <span>Las estimaciones no garantizan resultados.</span>
          </footer>
        </main>
      </div>
    </BrowserRouter>
  );
}
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

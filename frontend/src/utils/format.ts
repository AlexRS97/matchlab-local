export const pct = (value: number | null | undefined, signed = false) =>
  value == null
    ? "—"
    : `${signed && value > 0 ? "+" : ""}${(value * 100).toFixed(1)}${signed ? " pp" : "%"}`;
export const ev = (value: number | null | undefined) =>
  value == null ? "—" : `${value > 0 ? "+" : ""}${(value * 100).toFixed(1)}%`;
export const num = (value: number | null | undefined, digits = 2) =>
  value == null ? "—" : value.toFixed(digits);
export const marketName = (market: string) =>
  market.startsWith("BTTS")
    ? `Ambos marcan · ${market.endsWith("YES") ? "Sí" : "No"}`
    : `Over ${market.split("_")[1]}.5 ${market.endsWith("CORNERS") ? "córners" : "goles"}`;
export const localDate = () =>
  new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Madrid",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
export const time = (
  date: string | null | undefined,
  timezone = "Europe/Madrid",
) =>
  date
    ? new Date(date).toLocaleTimeString("es-ES", {
        timeZone: timezone,
        hour: "2-digit",
        minute: "2-digit",
      })
    : "—";
export const ago = (date: string | null | undefined) => {
  if (!date) return "Sin actualizar";
  const minutes = Math.max(
    0,
    Math.floor((Date.now() - new Date(date).getTime()) / 60000),
  );
  return minutes < 1
    ? "Ahora"
    : minutes < 60
      ? `hace ${minutes} min`
      : minutes < 1440
        ? `hace ${Math.floor(minutes / 60)} h`
        : `hace ${Math.floor(minutes / 1440)} d`;
};
export const normalize = (value: string) =>
  value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
export const modelName = (name: string) =>
  ({
    poisson: "Poisson",
    dixon_coles: "Dixon–Coles local",
    learned_mlp: "Red neuronal MLP",
    learned_gru: "Red recurrente GRU",
    learned_catboost: "CatBoost",
    learned_lightgbm: "LightGBM",
    learned_xgboost: "XGBoost",
    recent_form: "Forma reciente",
    home_away: "Casa / fuera",
    xg: "xG",
    external: "Externo",
    negative_binomial: "Binomial negativa",
  })[name] ?? name;

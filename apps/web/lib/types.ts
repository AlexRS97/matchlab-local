export type Team = { id: number; name: string; logo_url: string | null };
export type Competition = {
  id: number;
  name: string;
  country: string | null;
  logo_url: string | null;
  is_friendly: boolean;
  region: "Europa" | "América" | "Asia" | "África" | "Mundo" | "Otros";
  priority: number;
};

export type Recommendation = {
  market: string;
  selection: string;
  probability: number;
  confidence: number;
  rating: "fuerte" | "moderada" | "tendencia";
  kind: "valor" | "tendencia";
  rationale: string;
  decimal_odds: number | null;
  bookmaker: string | null;
  expected_value: number | null;
};

export type TeamInsight = {
  team_id: number;
  team_name: string;
  venue: "local" | "visitante";
  expected_goals: number;
  win_probability: number;
  avoid_defeat_probability: number;
  summary: string;
};

export type Prediction = {
  id: number;
  generated_at: string;
  model_version: string;
  home_expected_goals: number;
  away_expected_goals: number;
  total_expected_goals: number;
  home_expected_corners: number | null;
  away_expected_corners: number | null;
  total_expected_corners: number | null;
  home_win_probability: number;
  draw_probability: number;
  away_win_probability: number;
  over_2_5_probability: number;
  btts_probability: number;
  over_8_5_corners_probability: number | null;
  over_9_5_corners_probability: number | null;
  confidence: number;
  data_quality: "alta" | "media" | "baja";
  likely_scores: Array<{ score: string; probability: number }>;
  explanation: string[];
  recommendations: Recommendation[];
  team_insights: TeamInsight[];
};

export type Fixture = {
  id: number;
  provider_id: number;
  kickoff_at: string;
  status: string;
  status_long: string | null;
  round_name: string | null;
  venue_name: string | null;
  home_goals: number | null;
  away_goals: number | null;
  home_team: Team;
  away_team: Team;
  competition: Competition;
  prediction: Prediction | null;
};

export type DailyAnalysis = {
  date: string;
  timezone: string;
  total_fixtures: number;
  analyzed_fixtures: number;
  high_confidence_fixtures: number;
  recommended_fixtures: number;
  demo_mode: boolean;
  fixtures: Fixture[];
};

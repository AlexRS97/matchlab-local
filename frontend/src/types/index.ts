export type Bookmaker = "BETFAIR" | "BET365" | "WINAMAX";
export const BOOKMAKERS: Bookmaker[] = ["BETFAIR", "BET365", "WINAMAX"];
export const MARKETS = [
  "OVER_0_5_GOALS",
  "OVER_1_5_GOALS",
  "OVER_2_5_GOALS",
  "OVER_3_5_GOALS",
  "OVER_4_5_GOALS",
  "BTTS_YES",
  "BTTS_NO",
  "OVER_7_5_CORNERS",
  "OVER_8_5_CORNERS",
  "OVER_9_5_CORNERS",
  "OVER_10_5_CORNERS",
  "OVER_11_5_CORNERS",
];
export interface Grade {
  score: number;
  category: string;
  sample_size?: number;
  split_sample?: number;
  reasons?: string[];
  last_updated?: string | null;
  freshness?: number;
}
export interface Consensus {
  model_mean: number;
  model_std: number;
  model_min: number;
  model_max: number;
  model_count: number;
  model_disagreement: string;
}
export interface Model {
  name: string;
  status: string;
  reason?: string;
  probabilities: Record<string, number>;
  expected_home: number | null;
  expected_away: number | null;
  diagnostics: Record<string, unknown>;
}
export interface Ensemble {
  probabilities: Record<string, number>;
  expected_home?: number | null;
  expected_away?: number | null;
  expected_total?: number | null;
  models: Model[];
  consensus: Record<string, Consensus>;
  weights?: Record<string, Record<string, number>>;
}
export interface Prediction {
  learning?: {
    status: string;
    reason?: string;
    run_id?: string;
    trained_at?: string;
    models: Record<string, Record<string, number>>;
  };
  statistical_probabilities?: Record<string, Record<string, number>>;
  timestamp: string;
  goals: Ensemble;
  corners: Ensemble;
  quality: Grade;
  corner_quality?: Grade;
  confidence: Record<string, Grade>;
  features?: Features;
}
export interface Quote {
  provider: string;
  bookmaker: Bookmaker;
  decimal_odds: number;
  timestamp: string;
  stale: boolean;
  is_manual: boolean;
  is_delayed: boolean;
  source_label?: string;
  best_back_price?: number;
  best_lay_price?: number;
  market_probability: number;
  devig_status: string;
  edge: number | null;
  ev: number | null;
}
export interface Comparison {
  market: string;
  quotes: Record<Bookmaker, Quote | null>;
  model_probability: number | null;
  fair_odds: number | null;
  best_bookmaker: Bookmaker | null;
  best_odds: number | null;
  best: Quote | null;
  market_consensus: number | null;
  consensus_status: string;
  consensus_edge: number | null;
}
export interface Fixture {
  fixture_id: number;
  home_team: string;
  away_team: string;
  home_team_id: number;
  away_team_id: number;
  country: string;
  league_id: number;
  league_name: string;
  season: number;
  kickoff_utc: string;
  kickoff_local: string;
  status: string;
  updated_at: string;
  home_goals: number | null;
  away_goals: number | null;
  prediction: Prediction | null;
  markets: Record<string, Comparison>;
  search_names?: string[];
}
export interface Pick {
  rank: number;
  fixture: Fixture;
  market: string;
  probability: number;
  confidence: Grade;
  quality: Grade;
  comparison: Comparison;
  selected_quote: Quote;
}
export interface Job {
  running: boolean;
  date?: string;
  completed: number;
  total: number;
  errors: string[];
  finished_at?: string;
  stage?: string;
}
export interface TodayData {
  daily_analysis?: {
    hour: number;
    timezone: string;
    next_scheduled_at: string;
    due: boolean;
    last: {
      date: string;
      status: string;
      finished_at: string;
      fixtures: number;
      analysed: number;
    } | null;
  };
  date: string;
  timezone: string;
  fixtures_found: number;
  fixtures_analysed: number;
  complete_data: number;
  partial_data: number;
  insufficient_data: number;
  last_stats_update: string | null;
  last_odds_update: string | null;
  last_fixtures_update: string | null;
  fixtures: Fixture[];
  top_groups: Record<string, Pick[]>;
  job: Job;
}
export interface Summary {
  sample_size: number;
  source: string;
  last_updated?: string;
  goals_for?: number;
  goals_against?: number;
  total_goals_average?: number;
  over25_rate?: number;
  btts_rate?: number;
  shots?: number | null;
  shots_on_target?: number | null;
  xg?: number | null;
  xga?: number | null;
  corners_for?: number | null;
  corners_against?: number | null;
  average_total_corners?: number | null;
  corners_sample?: number;
  [key: string]: unknown;
}
export interface Observation {
  fixture_id: number;
  team_id: number;
  opponent_id: number;
  kickoff_utc: string;
  is_home: boolean;
  goals_for: number;
  goals_against: number;
  competition: string;
  corners_for: number | null;
  corners_against: number | null;
  source: string;
  observed_at: string;
}
export interface Standing {
  position: number;
  team_id: number;
  team: string;
  points: number;
  goal_difference: number;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goals_for: number;
  goals_against: number;
  source: string;
  observed_at: string;
}
export interface Features {
  home: Record<string, Summary>;
  away: Record<string, Summary>;
  home_split: Summary;
  away_split: Summary;
  league: Summary | null;
  standings: Standing[];
  h2h: { summary: Summary; matches: Observation[] };
  recent_home: Observation[];
  recent_away: Observation[];
  external?: {
    outcome_probabilities?: Record<string, number>;
    advice?: string;
    note?: string;
    timestamp?: string;
  };
}
export interface UserSettings {
  default_bookmaker: "ALL" | Bookmaker;
  minimum_odds: number;
  top_n: number;
  minimum_confidence: string;
  minimum_data_quality: string;
  enabled_bookmakers: Bookmaker[];
  enabled_markets: string[];
  enabled_countries: string[];
  enabled_leagues: number[];
  fixtures_minutes: number;
  standings_minutes: number;
  stats_minutes: number;
  betfair_minutes: number;
  pulsescore_minutes: number;
  odds_stale_minutes: number;
  betfair_fallback: boolean;
}
export interface ProviderState {
  provider: string;
  status: string;
  configured: boolean;
  requests_today: number;
  requests_period: number;
  requests_remaining: number;
  period: string;
  reset_time: string;
  last_success: string | null;
  last_error: string | null;
  delayed_prices?: boolean;
  effective_interval_minutes?: number;
  warnings?: string[];
}
export interface ProvidersData {
  providers: ProviderState[];
  bookmakers: { bookmaker: string; available_prices: number }[];
  job: Job;
}
export interface Analysis {
  paragraphs: string[];
  factors: { category: string; direction: string; text: string }[];
}
export interface MatchData {
  fixture: Fixture;
  prediction: Prediction | null;
}

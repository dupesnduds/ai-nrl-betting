export interface NRLTeam {
  id: string;
  name: string;
}

export interface PredictionModel {
  id: string;
  alias: string;
  port: number;
  apiUrl: string;
  tier: 'free' | 'premium'; // Added tier property
  description: string; // Added description property
}

export interface PredictionFormData {
  homeTeam: string | null;
  awayTeam: string | null;
  homeOdds?: number | null;
  awayOdds?: number | null;
  matchDate?: string | null; // YYYY-MM-DD format
  selectedModelAlias?: string;
}

// Structure matching the backend API request
export interface PredictionRequestPayload {
  team_a: string;
  team_b: string;
  match_date_str: string; // YYYY-MM-DD format
  odd_a?: number;
  odd_b?: number;
  odds_home_win?: number | null;
  odds_away_win?: number | null;
}

// Structure matching the backend API response
export interface PredictionResponseData {
  predicted_winner: string;
  // Backend might send individual probabilities instead of a single 'confidence'
  prob_home_win?: number; // Standard model home win prob
  prob_away_win?: number; // Standard model away win prob
  prob_draw?: number;     // Standard model draw prob
  prob_home_rl?: number;  // RL model home win prob
  prob_away_rl?: number;  // RL model away win prob
  prob_draw_rl?: number;  // RL model draw prob
  winner_confidence?: number; // RL model winner confidence
  overall_confidence?: number; // RL model overall confidence
  confidence?: number; // Generic confidence fallback
  margin?: number | [number, number]; // Optional margin (can be single number or tuple for RL)
  model_alias: string; // Backend should provide this
  model_name?: string; // Some backends might send this instead/as well
  // Add other potential RL fields if needed by UI later
  predicted_margin?: number | [number, number]; // RL specific margin field
  bookmaker_odds_home?: number;
  bookmaker_odds_away?: number;
  implied_prob_home_bookie?: number;
  implied_prob_away_bookie?: number;
  model_edge_vs_bookmaker?: number;
  gnn_embedding_similarity?: number;
  gnn_rivalry_score?: number;
  prediction_id?: number; // Added optional prediction ID from backend response
}

// Processed result for display (ensuring 'confidence' is present)
// Also includes fields needed for displaying past predictions
export interface PredictionResult extends Omit<PredictionResponseData, 'confidence' | 'prob_home_win' | 'prob_away_win' | 'prob_draw' | 'prob_home_rl' | 'prob_away_rl' | 'prob_draw_rl' | 'winner_confidence' | 'overall_confidence'> {
  confidence: number; // This will hold the relevant probability
  // Add fields needed for UserPredictions display as optional
  home_team_name?: string;
  away_team_name?: string;
  match_date?: string; // Date string
  prediction_timestamp?: string; // ISO string or similar
  prediction_id?: number; // ID from the database
  user_rating?: number; // Added optional user rating
  actual_winner?: string; // Added optional actual winner
  actual_margin?: number; // Added optional actual margin
  // Include other fields from PredictionResponseData implicitly
}

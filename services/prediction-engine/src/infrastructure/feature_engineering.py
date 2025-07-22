"""Feature engineering for prediction models."""

from typing import List, Dict, Any
import numpy as np
from datetime import datetime, timedelta

from ..domain.models import (
    Match, PredictionFeatures, TeamStats, FeatureEngineer, DataRepository
)


class StandardFeatureEngineer(FeatureEngineer):
    """Standard feature engineering implementation."""
    
    def __init__(self, data_repository: DataRepository):
        self.data_repository = data_repository
    
    async def extract_features(
        self, 
        match: Match, 
        historical_data: List[Match]
    ) -> PredictionFeatures:
        """Extract features for prediction."""
        
        # Get team statistics
        home_stats = await self.data_repository.get_team_stats(match.team_home)
        away_stats = await self.data_repository.get_team_stats(match.team_away)
        
        # Calculate ELO difference
        elo_difference = home_stats.elo_rating - away_stats.elo_rating
        
        # Calculate home advantage
        home_advantage = self._calculate_home_advantage(match.venue, home_stats)
        
        # Calculate head-to-head record
        h2h_record = self._calculate_head_to_head(
            match.team_home, 
            match.team_away, 
            historical_data
        )
        
        # Get recent encounters
        recent_encounters = self._get_recent_encounters(
            match.team_home, 
            match.team_away, 
            historical_data
        )
        
        # Calculate additional features
        additional_features = {
            "home_recent_scoring_avg": self._calculate_recent_scoring_average(
                match.team_home, historical_data, is_home=True
            ),
            "away_recent_scoring_avg": self._calculate_recent_scoring_average(
                match.team_away, historical_data, is_home=False
            ),
            "home_defensive_record": self._calculate_defensive_record(
                match.team_home, historical_data, is_home=True
            ),
            "away_defensive_record": self._calculate_defensive_record(
                match.team_away, historical_data, is_home=False
            ),
            "form_momentum": self._calculate_form_momentum(home_stats, away_stats),
            "rest_days": self._calculate_rest_days(match, historical_data),
            "season_stage": self._determine_season_stage(match.match_date),
            "rivalry_factor": self._calculate_rivalry_factor(
                match.team_home, match.team_away
            )
        }
        
        return PredictionFeatures(
            home_team_stats=home_stats,
            away_team_stats=away_stats,
            elo_difference=elo_difference,
            home_advantage=home_advantage,
            head_to_head_record=h2h_record,
            recent_encounters=recent_encounters,
            additional_features=additional_features
        )
    
    def _calculate_home_advantage(self, venue: str, home_stats: TeamStats) -> float:
        """Calculate home advantage factor."""
        base_home_advantage = 0.1  # 10% base advantage
        
        # Adjust based on team's home record
        if home_stats.home_win_rate:
            venue_factor = (home_stats.home_win_rate - 0.5) * 0.2
            return base_home_advantage + venue_factor
        
        return base_home_advantage
    
    def _calculate_head_to_head(
        self, 
        team_home: str, 
        team_away: str, 
        historical_data: List[Match]
    ) -> Dict[str, int]:
        """Calculate head-to-head record between teams."""
        h2h_record = {"home_wins": 0, "away_wins": 0, "draws": 0}
        
        for match in historical_data:
            if (match.team_home == team_home and match.team_away == team_away) or \
               (match.team_home == team_away and match.team_away == team_home):
                
                if match.home_score is None or match.away_score is None:
                    continue
                
                if match.home_score > match.away_score:
                    if match.team_home == team_home:
                        h2h_record["home_wins"] += 1
                    else:
                        h2h_record["away_wins"] += 1
                elif match.away_score > match.home_score:
                    if match.team_away == team_home:
                        h2h_record["home_wins"] += 1
                    else:
                        h2h_record["away_wins"] += 1
                else:
                    h2h_record["draws"] += 1
        
        return h2h_record
    
    def _get_recent_encounters(
        self, 
        team_home: str, 
        team_away: str, 
        historical_data: List[Match],
        limit: int = 5
    ) -> List[Match]:
        """Get recent encounters between the teams."""
        encounters = []
        
        for match in sorted(historical_data, key=lambda x: x.match_date, reverse=True):
            if (match.team_home == team_home and match.team_away == team_away) or \
               (match.team_home == team_away and match.team_away == team_home):
                encounters.append(match)
                
                if len(encounters) >= limit:
                    break
        
        return encounters
    
    def _calculate_recent_scoring_average(
        self, 
        team_name: str, 
        historical_data: List[Match], 
        is_home: bool,
        games: int = 5
    ) -> float:
        """Calculate recent scoring average for a team."""
        recent_scores = []
        
        for match in sorted(historical_data, key=lambda x: x.match_date, reverse=True):
            if is_home and match.team_home == team_name and match.home_score is not None:
                recent_scores.append(match.home_score)
            elif not is_home and match.team_away == team_name and match.away_score is not None:
                recent_scores.append(match.away_score)
            
            if len(recent_scores) >= games:
                break
        
        return np.mean(recent_scores) if recent_scores else 0.0
    
    def _calculate_defensive_record(
        self, 
        team_name: str, 
        historical_data: List[Match], 
        is_home: bool,
        games: int = 5
    ) -> float:
        """Calculate recent defensive record (points conceded)."""
        recent_conceded = []
        
        for match in sorted(historical_data, key=lambda x: x.match_date, reverse=True):
            if is_home and match.team_home == team_name and match.away_score is not None:
                recent_conceded.append(match.away_score)
            elif not is_home and match.team_away == team_name and match.home_score is not None:
                recent_conceded.append(match.home_score)
            
            if len(recent_conceded) >= games:
                break
        
        return np.mean(recent_conceded) if recent_conceded else 0.0
    
    def _calculate_form_momentum(
        self, 
        home_stats: TeamStats, 
        away_stats: TeamStats
    ) -> float:
        """Calculate form momentum difference."""
        home_momentum = self._team_form_to_score(home_stats.recent_form)
        away_momentum = self._team_form_to_score(away_stats.recent_form)
        
        return home_momentum - away_momentum
    
    def _team_form_to_score(self, recent_form: List[str]) -> float:
        """Convert recent form to a momentum score."""
        if not recent_form:
            return 0.0
        
        score = 0
        for i, result in enumerate(recent_form[-5:]):  # Last 5 games
            weight = (i + 1) / 5  # More recent games have higher weight
            if result == "W":
                score += 3 * weight
            elif result == "D":
                score += 1 * weight
            # Loss adds 0
        
        return score / len(recent_form[-5:])
    
    def _calculate_rest_days(
        self, 
        match: Match, 
        historical_data: List[Match]
    ) -> Dict[str, int]:
        """Calculate rest days for both teams."""
        home_rest = self._team_rest_days(match.team_home, match.match_date, historical_data)
        away_rest = self._team_rest_days(match.team_away, match.match_date, historical_data)
        
        return {"home_rest_days": home_rest, "away_rest_days": away_rest}
    
    def _team_rest_days(
        self, 
        team_name: str, 
        match_date: datetime, 
        historical_data: List[Match]
    ) -> int:
        """Calculate rest days for a team."""
        last_match_date = None
        
        for match in sorted(historical_data, key=lambda x: x.match_date, reverse=True):
            if match.match_date >= match_date:
                continue
                
            if match.team_home == team_name or match.team_away == team_name:
                last_match_date = match.match_date
                break
        
        if last_match_date:
            return (match_date - last_match_date).days
        
        return 7  # Default assumption
    
    def _determine_season_stage(self, match_date: datetime) -> str:
        """Determine what stage of the season the match is in."""
        # Simple implementation based on month
        month = match_date.month
        
        if month in [3, 4, 5]:
            return "early_season"
        elif month in [6, 7, 8]:
            return "mid_season"
        elif month in [9, 10]:
            return "finals"
        else:
            return "off_season"
    
    def _calculate_rivalry_factor(self, team_home: str, team_away: str) -> float:
        """Calculate rivalry factor between teams."""
        # Simple implementation - in reality would be based on historical data
        traditional_rivalries = {
            ("Brisbane Broncos", "North Queensland Cowboys"): 1.5,
            ("Sydney Roosters", "South Sydney Rabbitohs"): 1.8,
            ("Canterbury Bulldogs", "Parramatta Eels"): 1.3,
            # Add more rivalries as needed
        }
        
        rivalry_key = (team_home, team_away)
        reverse_key = (team_away, team_home)
        
        return traditional_rivalries.get(rivalry_key, 
               traditional_rivalries.get(reverse_key, 1.0))
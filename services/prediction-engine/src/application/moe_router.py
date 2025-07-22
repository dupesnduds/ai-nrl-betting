"""Mixture of Experts (MoE) routing system.

This module implements intelligent routing between the 5 prediction models
based on match characteristics, historical performance, and model strengths.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import numpy as np
from abc import ABC, abstractmethod

from ..domain.prediction_models import (
    PredictionModel, ModelType, PredictionType, MatchDetails, 
    PredictionResult, ModelMetrics
)

logger = logging.getLogger(__name__)


class RoutingStrategy(str, Enum):
    """Different routing strategies for MoE."""
    GATING_NETWORK = "gating_network"
    PERFORMANCE_BASED = "performance_based"
    ENSEMBLE_WEIGHTED = "ensemble_weighted"
    RULE_BASED = "rule_based"
    CONFIDENCE_BASED = "confidence_based"


@dataclass
class RoutingContext:
    """Context information for routing decisions."""
    
    match_details: MatchDetails
    team_rivalry_score: float = 0.0
    historical_h2h_matches: int = 0
    recent_form_differential: float = 0.0
    venue_advantage: float = 0.0
    season_stage: str = "regular"
    match_importance: float = 0.5
    data_availability: Dict[str, bool] = None
    
    def __post_init__(self):
        if self.data_availability is None:
            self.data_availability = {
                "historical_matches": True,
                "player_stats": True,
                "odds_data": True,
                "venue_data": True,
                "injury_reports": False
            }


@dataclass
class ModelPerformanceHistory:
    """Historical performance data for a model."""
    
    model_type: ModelType
    recent_accuracy: float
    overall_accuracy: float
    confidence_calibration: float
    strong_scenarios: List[str]
    weak_scenarios: List[str]
    last_updated: datetime
    prediction_count: int = 0


class RoutingEngine(ABC):
    """Abstract base class for routing engines."""
    
    @abstractmethod
    async def route(
        self, 
        context: RoutingContext,
        available_models: List[ModelType]
    ) -> Tuple[ModelType, float]:
        """Route to best model and return confidence in routing decision."""
        pass


class PerformanceBasedRouter(RoutingEngine):
    """Routes based on historical model performance."""
    
    def __init__(self):
        """Initialize performance tracker."""
        self.performance_history: Dict[ModelType, ModelPerformanceHistory] = {
            ModelType.LOGISTIC_REGRESSION: ModelPerformanceHistory(
                model_type=ModelType.LOGISTIC_REGRESSION,
                recent_accuracy=0.85,
                overall_accuracy=0.83,
                confidence_calibration=0.78,
                strong_scenarios=["simple_matchups", "clear_favorites"],
                weak_scenarios=["close_matches", "upset_predictions"],
                last_updated=datetime.utcnow()
            ),
            ModelType.LIGHTGBM: ModelPerformanceHistory(
                model_type=ModelType.LIGHTGBM,
                recent_accuracy=0.87,
                overall_accuracy=0.86,
                confidence_calibration=0.82,
                strong_scenarios=["feature_rich_matches", "regular_season"],
                weak_scenarios=["playoffs", "data_sparse_matches"],
                last_updated=datetime.utcnow()
            ),
            ModelType.TRANSFORMER: ModelPerformanceHistory(
                model_type=ModelType.TRANSFORMER,
                recent_accuracy=0.84,
                overall_accuracy=0.83,
                confidence_calibration=0.80,
                strong_scenarios=["sequence_patterns", "seasonal_trends"],
                weak_scenarios=["new_team_matchups", "irregular_patterns"],
                last_updated=datetime.utcnow()
            ),
            ModelType.STACKER: ModelPerformanceHistory(
                model_type=ModelType.STACKER,
                recent_accuracy=0.89,
                overall_accuracy=0.88,
                confidence_calibration=0.85,
                strong_scenarios=["balanced_matchups", "high_stakes_games"],
                weak_scenarios=["model_disagreement", "low_confidence_base_models"],
                last_updated=datetime.utcnow()
            ),
            ModelType.REINFORCEMENT_LEARNING: ModelPerformanceHistory(
                model_type=ModelType.REINFORCEMENT_LEARNING,
                recent_accuracy=0.91,
                overall_accuracy=0.90,
                confidence_calibration=0.88,
                strong_scenarios=["complex_interactions", "rivalry_matches"],
                weak_scenarios=["computational_constraints", "simple_patterns"],
                last_updated=datetime.utcnow()
            )
        }
    
    async def route(
        self, 
        context: RoutingContext,
        available_models: List[ModelType]
    ) -> Tuple[ModelType, float]:
        """Route based on model performance history."""
        
        model_scores = {}
        
        for model_type in available_models:
            if model_type not in self.performance_history:
                continue
                
            perf = self.performance_history[model_type]
            
            score = perf.recent_accuracy
            
            scenario_bonus = self._calculate_scenario_bonus(context, perf)
            score += scenario_bonus
            
            score += 0.1 * perf.confidence_calibration
            
            days_since_update = (datetime.utcnow() - perf.last_updated).days
            recency_penalty = min(0.05 * days_since_update, 0.2)
            score -= recency_penalty
            
            model_scores[model_type] = score
        
        if not model_scores:
            return ModelType.REINFORCEMENT_LEARNING, 0.5
        
        best_model = max(model_scores, key=model_scores.get)
        confidence = model_scores[best_model] / max(model_scores.values())
        
        logger.info(
            f"Performance-based routing selected {best_model.value}",
            extra={
                "scores": {k.value: v for k, v in model_scores.items()},
                "confidence": confidence
            }
        )
        
        return best_model, confidence
    
    def _calculate_scenario_bonus(
        self, 
        context: RoutingContext, 
        perf: ModelPerformanceHistory
    ) -> float:
        """Calculate bonus based on scenario match."""
        bonus = 0.0
        if context.team_rivalry_score > 0.7 and "rivalry_matches" in perf.strong_scenarios:
            bonus += 0.05
        
        if context.match_importance > 0.8 and "high_stakes_games" in perf.strong_scenarios:
            bonus += 0.05
        
        if context.season_stage == "playoffs" and "playoffs" in perf.strong_scenarios:
            bonus += 0.05
        elif context.season_stage == "playoffs" and "playoffs" in perf.weak_scenarios:
            bonus -= 0.05
        if not context.data_availability.get("historical_matches", True):
            if "data_sparse_matches" in perf.weak_scenarios:
                bonus -= 0.05
        
        return bonus


class RuleBasedRouter(RoutingEngine):
    """Routes based on hand-crafted rules."""
    
    async def route(
        self, 
        context: RoutingContext,
        available_models: List[ModelType]
    ) -> Tuple[ModelType, float]:
        """Route based on rules."""
        
        if (context.match_importance > 0.8 or context.team_rivalry_score > 0.7):
            if ModelType.REINFORCEMENT_LEARNING in available_models:
                return ModelType.REINFORCEMENT_LEARNING, 0.9
        if (context.historical_h2h_matches > 10 and 
            abs(context.recent_form_differential) < 0.3 and
            ModelType.STACKER in available_models):
            return ModelType.STACKER, 0.85
        if (context.season_stage == "regular" and 
            all(context.data_availability.values()) and
            ModelType.LIGHTGBM in available_models):
            return ModelType.LIGHTGBM, 0.8
        if (context.historical_h2h_matches > 15 and
            ModelType.TRANSFORMER in available_models):
            return ModelType.TRANSFORMER, 0.75
        if ModelType.LOGISTIC_REGRESSION in available_models:
            return ModelType.LOGISTIC_REGRESSION, 0.7
        return available_models[0], 0.5


class EnsembleWeightedRouter(RoutingEngine):
    """Routes to multiple models with weights."""
    
    async def route(
        self, 
        context: RoutingContext,
        available_models: List[ModelType]
    ) -> Tuple[ModelType, float]:
        """Select primary model for ensemble."""
        
        weights = {}
        
        for model_type in available_models:
            if model_type == ModelType.REINFORCEMENT_LEARNING:
                weights[model_type] = 0.35
            elif model_type == ModelType.STACKER:
                weights[model_type] = 0.25
            elif model_type == ModelType.LIGHTGBM:
                weights[model_type] = 0.20
            elif model_type == ModelType.TRANSFORMER:
                weights[model_type] = 0.15
            elif model_type == ModelType.LOGISTIC_REGRESSION:
                weights[model_type] = 0.05
        
        if context.match_importance > 0.8:
            if ModelType.REINFORCEMENT_LEARNING in weights:
                weights[ModelType.REINFORCEMENT_LEARNING] += 0.1
            if ModelType.STACKER in weights:
                weights[ModelType.STACKER] += 0.05
        if weights:
            primary_model = max(weights, key=weights.get)
            confidence = weights[primary_model]
            return primary_model, confidence
        
        return available_models[0], 0.5


class MixtureOfExpertsRouter:
    """Main MoE router that orchestrates different routing strategies."""
    
    def __init__(self, strategy: RoutingStrategy = RoutingStrategy.PERFORMANCE_BASED):
        """Initialize MoE router."""
        self.strategy = strategy
        self.routers = {
            RoutingStrategy.PERFORMANCE_BASED: PerformanceBasedRouter(),
            RoutingStrategy.RULE_BASED: RuleBasedRouter(),
            RoutingStrategy.ENSEMBLE_WEIGHTED: EnsembleWeightedRouter()
        }
        self.routing_history: List[Dict[str, Any]] = []
    
    async def route_prediction(
        self,
        match_details: MatchDetails,
        available_models: List[PredictionModel],
        prediction_type: PredictionType = PredictionType.MATCH_WINNER
    ) -> Tuple[PredictionModel, float, Dict[str, Any]]:
        """Route to the best model for this prediction."""
        
        start_time = time.time()
        
        context = await self._create_routing_context(match_details)
        
        available_model_types = [model.model_type for model in available_models]
        
        router = self.routers.get(self.strategy)
        if not router:
            router = self.routers[RoutingStrategy.PERFORMANCE_BASED]
        
        selected_model_type, confidence = await router.route(context, available_model_types)
        selected_model = None
        for model in available_models:
            if model.model_type == selected_model_type:
                selected_model = model
                break
        
        if not selected_model:
            selected_model = available_models[0]
            confidence = 0.5
        
        routing_time = (time.time() - start_time) * 1000
        routing_metadata = {
            "strategy": self.strategy.value,
            "selected_model": selected_model.model_type.value,
            "routing_confidence": confidence,
            "routing_time_ms": routing_time,
            "context": {
                "rivalry_score": context.team_rivalry_score,
                "match_importance": context.match_importance,
                "season_stage": context.season_stage,
                "h2h_matches": context.historical_h2h_matches
            },
            "available_models": [m.value for m in available_model_types]
        }
        self.routing_history.append({
            "timestamp": datetime.utcnow(),
            "match_id": match_details.match_id,
            "selected_model": selected_model.model_type.value,
            "confidence": confidence,
            "strategy": self.strategy.value
        })
        
        logger.info(
            f"MoE routing selected {selected_model.model_type.value}",
            extra=routing_metadata
        )
        
        return selected_model, confidence, routing_metadata
    
    async def _create_routing_context(self, match_details: MatchDetails) -> RoutingContext:
        """Create routing context from match details."""
        
        rivalry_score = self._calculate_rivalry_score(
            match_details.team_home, 
            match_details.team_away
        )
        
        match_importance = self._calculate_match_importance(match_details)
        season_stage = self._determine_season_stage(match_details.match_date)
        
        return RoutingContext(
            match_details=match_details,
            team_rivalry_score=rivalry_score,
            historical_h2h_matches=self._estimate_h2h_matches(
                match_details.team_home, 
                match_details.team_away
            ),
            match_importance=match_importance,
            season_stage=season_stage,
            data_availability={
                "historical_matches": True,
                "player_stats": True,
                "odds_data": match_details.odds_home is not None,
                "venue_data": match_details.venue is not None,
                "injury_reports": False
            }
        )
    
    def _calculate_rivalry_score(self, team_home: str, team_away: str) -> float:
        """Calculate rivalry score between teams."""
        rivalries = {
            ("Brisbane Broncos", "Melbourne Storm"): 0.8,
            ("Sydney Roosters", "South Sydney Rabbitohs"): 0.9,
            ("Manly Sea Eagles", "Sydney Roosters"): 0.7,
            ("Penrith Panthers", "Parramatta Eels"): 0.7,
            ("St George Dragons", "Canterbury Bulldogs"): 0.6,
        }
        rivalry = rivalries.get((team_home, team_away), 0.0)
        if rivalry == 0.0:
            rivalry = rivalries.get((team_away, team_home), 0.0)
        
        return rivalry
    
    def _calculate_match_importance(self, match_details: MatchDetails) -> float:
        """Calculate match importance."""
        importance = 0.5
        if match_details.round_num:
            if match_details.round_num > 20:
                importance = 0.9
            elif match_details.round_num > 15:
                importance = 0.7
        
        if match_details.match_date.month >= 9:
            importance = max(importance, 0.8)
        
        return min(importance, 1.0)
    
    def _determine_season_stage(self, match_date: datetime) -> str:
        """Determine what stage of season this match is in."""
        month = match_date.month
        
        if month in [3, 4, 5]:
            return "early_season"
        elif month in [6, 7, 8]:
            return "mid_season"
        elif month == 9:
            return "finals"
        elif month == 10:
            return "grand_final"
        else:
            return "off_season"
    
    def _estimate_h2h_matches(self, team_home: str, team_away: str) -> int:
        """Estimate historical head-to-head matches."""
        return np.random.randint(10, 30)
    
    def get_routing_statistics(self) -> Dict[str, Any]:
        """Get routing statistics."""
        if not self.routing_history:
            return {}
        
        recent_history = self.routing_history[-100:]
        
        model_usage = {}
        for decision in recent_history:
            model = decision["selected_model"]
            model_usage[model] = model_usage.get(model, 0) + 1
        
        avg_confidence = sum(d["confidence"] for d in recent_history) / len(recent_history)
        
        return {
            "total_routing_decisions": len(self.routing_history),
            "recent_model_usage": model_usage,
            "average_routing_confidence": avg_confidence,
            "current_strategy": self.strategy.value,
            "last_routing_time": recent_history[-1]["timestamp"].isoformat() if recent_history else None
        }
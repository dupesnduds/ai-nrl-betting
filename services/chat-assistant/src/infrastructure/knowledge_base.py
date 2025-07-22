"""Knowledge base implementations for chat assistant."""

from typing import Dict, List, Optional, Any
import httpx
from datetime import datetime

from ..domain.models import KnowledgeBase, ChatTopic


class StaticKnowledgeBase(KnowledgeBase):
    """Static knowledge base with pre-defined NRL information."""
    
    def __init__(self):
        """Initialise with static NRL data."""
        self.team_info = {
            "Brisbane Broncos": {
                "founded": 1988,
                "home_ground": "Suncorp Stadium",
                "coach": "Kevin Walters",
                "premierships": 6,
                "recent_form": ["W", "L", "W", "W", "L"],
                "key_players": ["Adam Reynolds", "Payne Haas", "Kotoni Staggs"],
                "strengths": ["Strong forward pack", "Experienced halves"],
                "weaknesses": ["Defensive lapses", "Consistency issues"]
            },
            "Sydney Roosters": {
                "founded": 1908,
                "home_ground": "Allianz Stadium",
                "coach": "Trent Robinson",
                "premierships": 15,
                "recent_form": ["W", "W", "L", "W", "W"],
                "key_players": ["James Tedesco", "Luke Keary", "Victor Radley"],
                "strengths": ["Clinical attack", "Strong leadership"],
                "weaknesses": ["Injury concerns", "Forward depth"]
            },
            "Melbourne Storm": {
                "founded": 1998,
                "home_ground": "AAMI Park",
                "coach": "Craig Bellamy",
                "premierships": 4,
                "recent_form": ["W", "W", "W", "L", "W"],
                "key_players": ["Cameron Munster", "Harry Grant", "Ryan Papenhuyzen"],
                "strengths": ["Structured play", "Defensive system"],
                "weaknesses": ["Ageing roster", "Succession planning"]
            }
            # Add more teams as needed
        }
        
        self.betting_tips = {
            "general": [
                "Never bet more than you can afford to lose",
                "Set a budget and stick to it",
                "Research team form and head-to-head records",
                "Consider weather conditions and venue",
                "Look for value in odds, not just favourites"
            ],
            "match_prediction": [
                "Analyse recent team performance",
                "Check for key player injuries",
                "Consider home ground advantage",
                "Look at head-to-head history",
                "Factor in motivation (finals, pride, etc.)"
            ],
            "player_props": [
                "Check player's recent scoring form",
                "Consider player's role in team structure",
                "Factor in opposition defensive strength",
                "Weather conditions can affect kicking games"
            ]
        }
    
    async def search_knowledge(
        self, 
        query: str, 
        topic: ChatTopic,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search knowledge base for relevant information."""
        results = []
        query_lower = query.lower()
        
        if topic == ChatTopic.TEAM_ANALYSIS:
            # Search team information
            for team_name, info in self.team_info.items():
                if any(word in team_name.lower() for word in query_lower.split()):
                    results.append({
                        "type": "team_info",
                        "team": team_name,
                        "data": info,
                        "relevance": 1.0
                    })
        
        elif topic == ChatTopic.BETTING_ADVICE:
            # Return relevant betting tips
            if "general" in query_lower or "basic" in query_lower:
                results.append({
                    "type": "betting_tips",
                    "category": "general",
                    "tips": self.betting_tips["general"][:limit],
                    "relevance": 1.0
                })
            elif "prediction" in query_lower or "match" in query_lower:
                results.append({
                    "type": "betting_tips",
                    "category": "match_prediction",
                    "tips": self.betting_tips["match_prediction"][:limit],
                    "relevance": 1.0
                })
        
        return results[:limit]
    
    async def get_team_info(self, team_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific team."""
        # Normalise team name
        for stored_team, info in self.team_info.items():
            if team_name.lower() in stored_team.lower() or stored_team.lower() in team_name.lower():
                return {
                    "team_name": stored_team,
                    **info
                }
        
        return None
    
    async def get_recent_predictions(
        self, 
        team_home: str, 
        team_away: str
    ) -> Optional[Dict[str, Any]]:
        """Get recent predictions for a match."""
        # This would typically call the prediction service
        # For now, return mock data
        return {
            "teams": f"{team_home} vs {team_away}",
            "prediction": f"{team_home} favoured",
            "confidence": 0.65,
            "key_factors": [
                "Recent form advantage",
                "Home ground benefit",
                "Head-to-head record"
            ],
            "timestamp": datetime.utcnow().isoformat()
        }


class LiveKnowledgeBase(KnowledgeBase):
    """Knowledge base that fetches live data from prediction services."""
    
    def __init__(self, prediction_service_url: str):
        """Initialise with prediction service URL."""
        self.prediction_service_url = prediction_service_url
        self.static_kb = StaticKnowledgeBase()  # Fallback to static data
    
    async def search_knowledge(
        self, 
        query: str, 
        topic: ChatTopic,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search knowledge with live data."""
        # Try to get live data first, fall back to static
        try:
            # For team analysis, combine static info with live stats
            if topic == ChatTopic.TEAM_ANALYSIS:
                static_results = await self.static_kb.search_knowledge(query, topic, limit)
                
                # TODO: Enhance with live team statistics
                # live_stats = await self._fetch_live_team_stats(team_name)
                
                return static_results
            
            else:
                return await self.static_kb.search_knowledge(query, topic, limit)
                
        except Exception:
            # Fallback to static knowledge
            return await self.static_kb.search_knowledge(query, topic, limit)
    
    async def get_team_info(self, team_name: str) -> Optional[Dict[str, Any]]:
        """Get team information with live data."""
        try:
            # Get static info first
            static_info = await self.static_kb.get_team_info(team_name)
            
            if static_info:
                # TODO: Enhance with live statistics
                # live_stats = await self._fetch_live_team_stats(team_name)
                # static_info.update(live_stats)
                
                return static_info
            
            return None
            
        except Exception:
            return await self.static_kb.get_team_info(team_name)
    
    async def get_recent_predictions(
        self, 
        team_home: str, 
        team_away: str
    ) -> Optional[Dict[str, Any]]:
        """Get recent predictions from live prediction service."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.prediction_service_url}/api/v1/teams/{team_home}/stats"
                )
                
                if response.status_code == 200:
                    # TODO: Process live prediction data
                    # For now, return static mock data
                    pass
                    
        except Exception:
            # Fallback to static data
            pass
        
        return await self.static_kb.get_recent_predictions(team_home, team_away)
    
    async def _fetch_live_team_stats(self, team_name: str) -> Dict[str, Any]:
        """Fetch live team statistics."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.prediction_service_url}/api/v1/teams/{team_name}/stats",
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    return response.json()
                
        except Exception:
            pass
        
        return {}
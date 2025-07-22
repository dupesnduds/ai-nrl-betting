"""Topic classification for chat messages."""

import re
from typing import Dict, List
from ..domain.models import TopicClassifier, ChatTopic


class SimpleTopicClassifier(TopicClassifier):
    """Simple rule-based topic classifier for NRL chat."""
    
    def __init__(self):
        """Initialise the topic classifier with keyword patterns."""
        self.topic_patterns = {
            ChatTopic.MATCH_PREDICTION: [
                r'\b(predict|prediction|forecast|odds|win|lose|beat)\b',
                r'\b(vs|against|v\.s|versus)\b',
                r'\b(match|game|round)\b',
                r'\b(who will win|winner|outcome)\b'
            ],
            ChatTopic.TEAM_ANALYSIS: [
                r'\b(team|analysis|performance|form|stats|statistics)\b',
                r'\b(how are|how is|tell me about)\b.*\b(broncos|roosters|storm|panthers|cowboys|rabbitohs|bulldogs|eels|knights|sharks|dragons|tigers|titans|eagles|warriors|raiders)\b',
                r'\b(strengths|weaknesses|lineup|squad)\b'
            ],
            ChatTopic.PLAYER_STATS: [
                r'\b(player|players|stats|statistics|points|tries|goals)\b',
                r'\b(best|top|leading|scorer|kicker)\b',
                r'\b(injury|injuries|injured|fit|fitness)\b'
            ],
            ChatTopic.BETTING_ADVICE: [
                r'\b(bet|betting|wager|stake|strategy|advice|tip|tips)\b',
                r'\b(should i|recommend|suggestion|best bet)\b',
                r'\b(odds|payout|return|profit|risk)\b',
                r'\b(how much|bankroll|money management)\b'
            ],
            ChatTopic.GENERAL_NRL: [
                r'\b(nrl|rugby league|season|round|finals|grand final)\b',
                r'\b(ladder|standings|table|points)\b',
                r'\b(news|latest|update|recent)\b'
            ]
        }
        
        # NRL team names for better matching
        self.nrl_teams = [
            "brisbane broncos", "broncos",
            "sydney roosters", "roosters",
            "melbourne storm", "storm",
            "penrith panthers", "panthers",
            "north queensland cowboys", "cowboys",
            "south sydney rabbitohs", "rabbitohs", "souths",
            "canterbury bulldogs", "bulldogs", "dogs",
            "parramatta eels", "eels",
            "newcastle knights", "knights",
            "cronulla sharks", "sharks",
            "st george illawarra dragons", "dragons",
            "wests tigers", "tigers",
            "gold coast titans", "titans",
            "manly sea eagles", "eagles", "manly",
            "new zealand warriors", "warriors",
            "canberra raiders", "raiders"
        ]
    
    async def classify_topic(self, message: str) -> ChatTopic:
        """Classify the topic of a message."""
        message_lower = message.lower()
        
        # Score each topic based on pattern matches
        topic_scores = {topic: 0 for topic in ChatTopic}
        
        # Check for team mentions (increases likelihood of sports-related topics)
        team_mentions = sum(1 for team in self.nrl_teams if team in message_lower)
        
        # Score based on patterns
        for topic, patterns in self.topic_patterns.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, message_lower))
                topic_scores[topic] += matches
        
        # Boost team-related topics if teams are mentioned
        if team_mentions > 0:
            topic_scores[ChatTopic.TEAM_ANALYSIS] += team_mentions
            topic_scores[ChatTopic.MATCH_PREDICTION] += team_mentions * 0.5
        
        # Special logic for prediction vs analysis
        if team_mentions >= 2:  # Two teams mentioned likely means prediction
            topic_scores[ChatTopic.MATCH_PREDICTION] += 2
        
        # Check for specific prediction indicators
        prediction_indicators = [
            "predict", "forecast", "odds", "vs", "versus", "against",
            "who will win", "winner", "beat", "defeat"
        ]
        
        for indicator in prediction_indicators:
            if indicator in message_lower:
                topic_scores[ChatTopic.MATCH_PREDICTION] += 1
        
        # Check for betting advice indicators
        betting_indicators = [
            "should i bet", "recommend", "advice", "tip", "strategy",
            "best bet", "good bet", "worth betting"
        ]
        
        for indicator in betting_indicators:
            if indicator in message_lower:
                topic_scores[ChatTopic.BETTING_ADVICE] += 2
        
        # Find the highest scoring topic
        best_topic = max(topic_scores.items(), key=lambda x: x[1])
        
        # Return the best topic if it has a meaningful score, otherwise OTHER
        if best_topic[1] > 0:
            return best_topic[0]
        else:
            return ChatTopic.OTHER
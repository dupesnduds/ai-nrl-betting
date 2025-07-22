#!/usr/bin/env python3
"""
Validation script for LR migration.
Tests that the migrated predictor produces same results as original.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add paths
project_root = Path(__file__).parent.parent.parent.parent.parent
lr_predictor_path = project_root / "logistic-regression-predictor"
sys.path.append(str(lr_predictor_path))
sys.path.append(str(Path(__file__).parent / "src"))

print(f"Project root: {project_root}")
print(f"LR predictor path: {lr_predictor_path}")
print(f"LR predictor exists: {lr_predictor_path.exists()}")

# Test data
sample_match = {
    "team_home": "Brisbane Broncos",
    "team_away": "Sydney Roosters", 
    "date": "2024-03-15",
    "odds_home": 2.50,
    "odds_away": 1.60
}

def test_original_predictor():
    """Test original LR predictor."""
    print("\n=== Testing Original Predictor ===")
    
    try:
        from logistic_regression_predictor import workflow
        print("SUCCESS: Successfully imported original workflow")
        
        # Test prediction
        result = workflow.run_prediction_workflow(
            team_a=sample_match["team_home"],
            team_b=sample_match["team_away"],
            match_date_str=sample_match["date"],
            odd_a=sample_match["odds_home"],
            odd_b=sample_match["odds_away"]
        )
        
        if result:
            print("SUCCESS: Original prediction successful")
            print(f"  Predicted winner: {result.get('predicted_winner', 'unknown')}")
            print(f"  Home probability: {result.get('prob_home_win', 0.0):.3f}")
            print(f"  Away probability: {result.get('prob_away_win', 0.0):.3f}")
            return result
        else:
            print("FAILED: Original prediction failed - returned None")
            return None
            
    except ImportError as e:
        print(f"FAILED: Could not import original predictor: {e}")
        return None
    except Exception as e:
        print(f"FAILED: Original prediction error: {e}")
        return None

async def test_migrated_predictor():
    """Test migrated LR predictor."""
    print("\n=== Testing Migrated Predictor ===")
    
    try:
        from domain.prediction_models import MatchDetails, PredictionType
        from infrastructure.models.lr_predictor import LogisticRegressionPredictor
        print("SUCCESS: Successfully imported migrated predictor")
        
        # Create match details
        match_details = MatchDetails(
            team_home=sample_match["team_home"],
            team_away=sample_match["team_away"],
            match_date=datetime.strptime(sample_match["date"], "%Y-%m-%d"),
            odds_home=sample_match["odds_home"],
            odds_away=sample_match["odds_away"]
        )
        
        # Test prediction
        predictor = LogisticRegressionPredictor()
        is_ready = await predictor.is_ready()
        
        if not is_ready:
            print("FAILED: Migrated predictor not ready")
            return None
        
        print("SUCCESS: Migrated predictor is ready")
        
        result = await predictor.predict(match_details)
        
        if result:
            print("SUCCESS: Migrated prediction successful")
            print(f"  Predicted winner: {result.predicted_winner.value}")
            print(f"  Home probability: {result.probabilities.get('home', 0.0):.3f}")
            print(f"  Away probability: {result.probabilities.get('away', 0.0):.3f}")
            print(f"  Processing time: {result.processing_time_ms:.2f}ms")
            return result
        else:
            print("FAILED: Migrated prediction failed - returned None")
            return None
            
    except ImportError as e:
        print(f"FAILED: Could not import migrated predictor: {e}")
        import traceback
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"FAILED: Migrated prediction error: {e}")
        import traceback
        traceback.print_exc()
        return None

def compare_results(original, migrated):
    """Compare original and migrated results."""
    print("\n=== Comparing Results ===")
    
    if not original or not migrated:
        print("FAILED: Cannot compare - one or both predictions failed")
        return False
    
    # Compare winners
    original_winner = original.get('predicted_winner', '').lower()
    migrated_winner = migrated.predicted_winner.value.lower()
    
    if original_winner == migrated_winner:
        print(f"SUCCESS: Winners match: {original_winner}")
    else:
        print(f"FAILED: Winners differ: {original_winner} vs {migrated_winner}")
        return False
    
    # Compare probabilities
    original_prob_home = original.get('prob_home_win', 0.0)
    original_prob_away = original.get('prob_away_win', 0.0)
    
    migrated_prob_home = migrated.probabilities.get('home', 0.0)
    migrated_prob_away = migrated.probabilities.get('away', 0.0)
    
    tolerance = 0.001
    home_diff = abs(original_prob_home - migrated_prob_home)
    away_diff = abs(original_prob_away - migrated_prob_away)
    
    if home_diff < tolerance and away_diff < tolerance:
        print(f"SUCCESS: Probabilities match within tolerance ({tolerance})")
        print(f"  Home: {original_prob_home:.3f} vs {migrated_prob_home:.3f} (diff: {home_diff:.6f})")
        print(f"  Away: {original_prob_away:.3f} vs {migrated_prob_away:.3f} (diff: {away_diff:.6f})")
        return True
    else:
        print(f"FAILED: Probabilities differ beyond tolerance ({tolerance})")
        print(f"  Home: {original_prob_home:.3f} vs {migrated_prob_home:.3f} (diff: {home_diff:.6f})")
        print(f"  Away: {original_prob_away:.3f} vs {migrated_prob_away:.3f} (diff: {away_diff:.6f})")
        return False

async def main():
    """Main validation function."""
    print("LR Migration Validation")
    print("=" * 50)
    
    # Test original
    original_result = test_original_predictor()
    
    # Test migrated
    migrated_result = await test_migrated_predictor()
    
    # Compare
    success = compare_results(original_result, migrated_result)
    
    print("\n" + "=" * 50)
    if success:
        print("MIGRATION VALIDATION SUCCESSFUL!")
        print("The migrated predictor produces identical results to the original.")
    else:
        print("MIGRATION VALIDATION FAILED!")
        print("The migrated predictor does not match the original results.")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())
# AI Betting Platform

Machine learning platform for NRL match predictions using multiple models.

## Services

- **Real Models API** (port 8001) - Prediction engine with trained models
- **Frontend** (port 3001) - React web interface

## Models

- Logistic Regression
- LightGBM 
- Stacker Ensemble

## Development

```bash
# Backend
source backend_env/bin/activate
python real_models_api.py

# Frontend  
cd frontend
npm run dev
```

## Structure

- `/data/models/trained/` - Trained model files
- `/frontend/` - React TypeScript application
- `real_models_api.py` - FastAPI prediction service

## Model Files

Pre-trained model files are included in the repository:

- `logistic_regression_model.joblib` (3KB)
- `lgbm_match_winner_model.joblib` (967KB)  
- `stacker_match_winner_model.joblib` (561KB)
- `transformer_predictor_model.pth` (428KB)
- Label encoders and calibrators

## Requirements

- Python 3.12+
- Node.js 18+
- Trained model files (available on request)
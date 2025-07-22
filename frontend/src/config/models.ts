import { PredictionModel } from '../types';

const BASE_URL = 'http://localhost'; // Assuming backend runs locally

export const PREDICTION_MODELS: PredictionModel[] = [
  {
    id: 'lr',
    alias: 'Quick Pick',
    port: 8001,
    apiUrl: `${BASE_URL}:8001/predict`,
    tier: 'free',
    description: 'Fast baseline prediction.',
  },
  {
    id: 'lgbm',
    alias: 'Form Cruncher', // Keeping this alias as requested
    port: 8002,
    apiUrl: `${BASE_URL}:8002/predict`,
    tier: 'free',
    description: 'Balanced performance model.',
  },
  // Stacker moved down
  {
    id: 'transformer',
    alias: 'Deep Dive',
    port: 8004,
    apiUrl: `${BASE_URL}:8004/predict`,
    tier: 'premium',
    description: 'Context-aware transformer model.',
  },
  {
    id: 'stacker',
    alias: 'Stacked', // Changed alias
    port: 8003,
    apiUrl: `${BASE_URL}:8003/predict`,
    tier: 'premium',
    description: 'Ensemble model for higher accuracy.', // Kept original description
  },
  {
    id: 'rl',
    alias: 'Edge Finder',
    port: 8006, // Changed port
    apiUrl: `${BASE_URL}:8006/predict`, // Changed port in URL
    tier: 'premium',
    description: 'Reinforcement learning agent.',
  },
];

// Default model to use if user is not paid or doesn't select
export const DEFAULT_MODEL_ALIAS = 'Quick Pick';

export const getModelByAlias = (alias: string): PredictionModel | undefined => {
  return PREDICTION_MODELS.find(model => model.alias === alias);
};

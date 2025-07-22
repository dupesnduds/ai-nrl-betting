import React, { useState } from 'react';
import PredictionForm from './PredictionForm';
import PredictionOutput from './PredictionOutput';
import { PredictionRequestPayload, PredictionResult } from '../types';
import { getPrediction } from '../services/predictionAPI';
import RightPanel from './Layout/RightPanel';

const MainPredictionView: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [predictionResult, setPredictionResult] = useState<PredictionResult | null>(null);

  // Update handlePredict to accept the idToken
  const handlePredict = async (payload: PredictionRequestPayload, modelAlias: string, idToken: string | null) => {
    setLoading(true);
    setError(null);
    setPredictionResult(null); // Clear previous result

    try {
      // Pass the idToken to getPrediction
      const result = await getPrediction(payload, modelAlias, idToken);
      setPredictionResult(result);
    } catch (err: any) {
      console.error("Prediction failed:", err);
      setError(err.message || 'An unknown error occurred while fetching the prediction.');
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className="predictions-container">
      <div style={{ flex: 1 }}>
        <PredictionForm onSubmit={handlePredict} isLoading={loading} />
        <PredictionOutput
          loading={loading}
          error={error}
          predictionResult={predictionResult}
        />
      </div>
      <RightPanel />
    </div>
  );
};

export default MainPredictionView;

import { PredictionRequestPayload, PredictionResult, PredictionResponseData } from '../types'; // Import PredictionResponseData
import { getModelByAlias } from '../config/models';

// Use console for logging in frontend service files unless a proper logger is set up
const logger = console; // Simple alias for consistency, replace with actual logger if needed

const USER_SERVICE_BASE_URL = 'http://localhost:8007'; // Define base URL for user service

export const getPrediction = async (
  payload: PredictionRequestPayload,
  modelAlias: string,
  idToken: string | null = null // Add optional idToken parameter
): Promise<PredictionResult> => {
  const model = getModelByAlias(modelAlias);

  if (!model) {
    throw new Error(`Configuration error: Model with alias "${modelAlias}" not found.`);
  }

  console.log(`Sending prediction request to ${model.apiUrl} with payload:`, payload);

  try {
    // Prepare headers
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    // Add Authorization header if token is provided
    if (idToken) {
      headers['Authorization'] = `Bearer ${idToken}`;
      console.log(`Including Authorization header for model ${modelAlias}`);
    } else {
      console.log(`No ID token provided for model ${modelAlias}, sending unauthenticated request.`);
    }

    const response = await fetch(model.apiUrl, {
      method: 'POST',
      headers: headers, // Use the prepared headers object
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      // Attempt to read error details from the response body
      let errorBody = null;
      try {
        errorBody = await response.json();
      } catch (e) {
        // Ignore if response body is not JSON or empty
      }
      console.error("API Error Response:", errorBody);
      throw new Error(
        `API request failed with status ${response.status}: ${response.statusText}. ${errorBody?.detail || 'No additional details.'}`
      );
    }

    const rawData: PredictionResponseData = await response.json();

    // --- Process the raw data to create the PredictionResult ---
    let confidence = 0; // Default confidence
    const winner = rawData.predicted_winner;

    // Determine confidence based on the predicted winner and available probabilities
    // Check for RL-specific fields first
    if (winner === 'Home' && rawData.prob_home_rl !== undefined) { // Check RL field and 'Home' winner
        confidence = rawData.prob_home_rl;
    } else if (winner === 'Away' && rawData.prob_away_rl !== undefined) { // Check RL field and 'Away' winner
        confidence = rawData.prob_away_rl;
    } else if (winner === 'Draw' && rawData.prob_draw_rl !== undefined) { // Check RL field
        confidence = rawData.prob_draw_rl;
    // Then check for standard fields (from other models)
    } else if (winner === 'Home Win' && rawData.prob_home_win !== undefined) { // Check standard field
      confidence = rawData.prob_home_win;
    } else if (winner === 'Away Win' && rawData.prob_away_win !== undefined) { // Check standard field
      confidence = rawData.prob_away_win;
    } else if (winner === 'Draw' && rawData.prob_draw !== undefined) { // Check standard field
      confidence = rawData.prob_draw;
    // Fallback to generic confidence fields
    } else if (rawData.winner_confidence !== undefined) { // Check RL winner_confidence
        confidence = rawData.winner_confidence;
        logger.warn("Using fallback 'winner_confidence' field from backend.");
    } else if (rawData.overall_confidence !== undefined) { // Check RL overall_confidence
        confidence = rawData.overall_confidence;
        logger.warn("Using fallback 'overall_confidence' field from backend.");
    } else if (rawData.confidence !== undefined) { // Check generic confidence
      // Fallback to using 'confidence' field if specific probabilities aren't available
      confidence = rawData.confidence;
      logger.warn("Using fallback generic 'confidence' field from backend.");
    } else {
       logger.warn(`Could not determine confidence for predicted winner '${winner}'. Using 0.`);
    }

    // Ensure the model_alias is present (use requested alias as fallback)
    const finalAlias = rawData.model_alias || rawData.model_name || modelAlias;
    if (!rawData.model_alias && !rawData.model_name) {
        console.warn("Backend response missing 'model_alias' and 'model_name', using requested alias as fallback.");
    } else if (rawData.model_alias && rawData.model_alias !== modelAlias) {
         console.warn(`Backend returned alias '${rawData.model_alias}' but requested '${modelAlias}'. Using backend alias.`);
    } else if (rawData.model_name && rawData.model_name !== modelAlias) {
         // Less critical warning if model_name differs but alias matches or was missing
         console.info(`Backend model_name '${rawData.model_name}' differs from requested alias '${modelAlias}'.`);
    }

    // Construct the final PredictionResult object for the UI
    const resultData: PredictionResult = {
        predicted_winner: winner,
        confidence: confidence, // Use the determined confidence
        margin: rawData.margin, // Pass margin if it exists
        model_alias: finalAlias, // Use the determined alias
        // Include any other relevant fields from rawData if needed, excluding the specific prob fields
        // Add prediction_id if backend provides it directly in the prediction response
        prediction_id: rawData.prediction_id, // Assuming backend might return this
    };


    console.log("Processed prediction response:", resultData);
    return resultData;

  } catch (error) {
    console.error('Network or API call error:', error);
    // Re-throw the error to be caught by the calling component
    throw error;
  }
};

// --- Function to fetch user's past predictions ---
export const getUserPredictions = async (idToken: string): Promise<PredictionResult[]> => {
  const userServiceUrl = `${USER_SERVICE_BASE_URL}/users/me/predictions`;
  logger.log(`Fetching user predictions from ${userServiceUrl}`);

  try {
    const response = await fetch(userServiceUrl, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${idToken}`,
        'Content-Type': 'application/json', // Content-Type might not be strictly needed for GET but good practice
      },
    });

    if (!response.ok) {
      let errorBody = null;
      try {
        errorBody = await response.json();
      } catch (e) { /* Ignore */ }
      logger.error("API Error Response (getUserPredictions):", errorBody);
      throw new Error(
        `API request failed with status ${response.status}: ${response.statusText}. ${errorBody?.detail || 'No additional details.'}`
      );
    }

    // The backend returns List[models.UserPrediction]
    // We need to map this to the frontend's PredictionResult[] type
    const rawPredictions: any[] = await response.json(); // Type as any[] for flexibility during mapping

    const processedPredictions: PredictionResult[] = rawPredictions.map(rawPred => {
      // Similar confidence logic as in getPrediction, adapt as needed based on UserPrediction model fields
      let confidence = 0;
      const winner = rawPred.predicted_winner; // Use the winner field from the UserPrediction model

      if (winner === 'Home' && rawPred.prob_home_rl !== undefined) {
          confidence = rawPred.prob_home_rl;
      } else if (winner === 'Away' && rawPred.prob_away_rl !== undefined) {
          confidence = rawPred.prob_away_rl;
      } else if (winner === 'Draw' && rawPred.prob_draw_rl !== undefined) {
          confidence = rawPred.prob_draw_rl;
      } else if (winner === 'Home Win' && rawPred.prob_home_win !== undefined) {
        confidence = rawPred.prob_home_win;
      } else if (winner === 'Away Win' && rawPred.prob_away_win !== undefined) {
        confidence = rawPred.prob_away_win;
      } else if (winner === 'Draw' && rawPred.prob_draw !== undefined) {
        confidence = rawPred.prob_draw;
      } else if (rawPred.winner_confidence !== undefined) {
          confidence = rawPred.winner_confidence;
      } else if (rawPred.overall_confidence !== undefined) {
          confidence = rawPred.overall_confidence;
      } else {
         logger.warn(`Could not determine confidence for prediction ID ${rawPred.prediction_id}. Using 0.`);
      }

      // Map to PredictionResult structure
      return {
        predicted_winner: winner,
        confidence: confidence,
        model_alias: rawPred.model, // Use the 'model' field from UserPrediction
        // Add other fields if needed and available in UserPrediction
        // e.g., match_date, home_team_name, away_team_name?
        // These might be useful for display
        match_date: rawPred.match_date,
        home_team_name: rawPred.home_team_name,
        away_team_name: rawPred.away_team_name,
        prediction_timestamp: rawPred.prediction_timestamp, // Keep timestamp
        prediction_id: rawPred.prediction_id, // Keep original prediction ID
      };
    });

    logger.log(`Successfully fetched and processed ${processedPredictions.length} user predictions.`);
    return processedPredictions;

  } catch (error) {
    logger.error('Error fetching user predictions:', error);
    throw error; // Re-throw
  }
};

// --- Function to submit prediction quality rating ---
export const submitPredictionRating = async (
  predictionId: number, // Assuming prediction_id is a number based on types
  rating: number,
  idToken: string
): Promise<void> => {
  const ratingUrl = `${USER_SERVICE_BASE_URL}/users/feedback/rating`;
  logger.log(`Submitting prediction rating to ${ratingUrl}`);

  try {
    const response = await fetch(ratingUrl, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${idToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        prediction_id: predictionId,
        rating_value: rating,
      }),
    });

    if (!response.ok) {
      let errorBody = null;
      try {
        errorBody = await response.json();
      } catch (e) { /* Ignore */ }
      logger.error("API Error Response (submitPredictionRating):", errorBody);
      throw new Error(
        `API request failed with status ${response.status}: ${response.statusText}. ${errorBody?.detail || 'No additional details.'}`
      );
    }

    // Check for successful response (e.g., 200 OK or 201 Created)
    logger.log(`Prediction rating submitted successfully for prediction ID: ${predictionId}`);
    // No specific content expected in the response body for success

  } catch (error) {
    logger.error('Error submitting prediction rating:', error);
    throw error; // Re-throw
  }
};

// --- Placeholder for submitting actual match result ---
// TODO: Implement submitActualResult function
export const submitActualResult = async (
  predictionId: number, // Assuming prediction_id is a number
  winner: string,
  margin: number,
  idToken: string
): Promise<void> => {
  const resultUrl = `${USER_SERVICE_BASE_URL}/users/feedback/result`;
  logger.log(`Submitting actual result to ${resultUrl}`);
  logger.warn("submitActualResult function is not fully implemented yet.");

  // Placeholder implementation - replace with actual fetch call
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      logger.log(`Placeholder: Would submit result for prediction ID: ${predictionId}`);
      // Simulate success for now
      resolve();
      // To simulate failure:
      // reject(new Error("Simulated backend error saving result."));
    }, 500); // Simulate network delay
  });

  // --- Actual Implementation (when backend is ready) ---
  /*
  try {
    const response = await fetch(resultUrl, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${idToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        prediction_id: predictionId,
        actual_winner: winner,
        actual_margin: margin,
      }),
    });

    if (!response.ok) {
      let errorBody = null;
      try { errorBody = await response.json(); } catch (e) { }
      logger.error("API Error Response (submitActualResult):", errorBody);
      throw new Error(
        `API request failed with status ${response.status}: ${response.statusText}. ${errorBody?.detail || 'No additional details.'}`
      );
    }
    logger.log(`Actual result submitted successfully for prediction ID: ${predictionId}`);

  } catch (error) {
    logger.error('Error submitting actual result:', error);
    throw error;
  }
  */
};

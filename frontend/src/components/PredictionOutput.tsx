import React, { useState } from 'react'; // Added useState
import { Spin, Alert, Typography, Space, Button, message, Divider, Rate } from 'antd'; // Removed Card, Added Rate
import { CopyOutlined, ShareAltOutlined } from '@ant-design/icons'; // Removed Like/Dislike icons
import { PredictionResult } from '../types';
import { useAuth } from '../contexts/AuthContext'; // Added useAuth
import { submitPredictionRating } from '../services/predictionAPI'; // Added service function

const { Title, Text, Paragraph } = Typography;

interface PredictionOutputProps {
  loading: boolean;
  error: string | null;
  predictionResult: PredictionResult | null;
}

const PredictionOutput: React.FC<PredictionOutputProps> = ({ loading, error, predictionResult }) => {
  const { currentUser } = useAuth(); // Get user context
  const [ratingValue, setRatingValue] = useState<number>(0); // State for the current rating
  const [isRatingLoading, setIsRatingLoading] = useState<boolean>(false); // State for rating submission loading
  const [ratingSubmitted, setRatingSubmitted] = useState<boolean>(false); // State to track if rating was submitted

  const handleCopy = () => {
    if (predictionResult) {
      const predictionText = `${predictionResult.model_alias} predicts: ${predictionResult.predicted_winner} to win (Confidence: ${(predictionResult.confidence * 100).toFixed(1)}%)${predictionResult.margin ? ` | Margin: ${predictionResult.margin}` : ''}`;
      navigator.clipboard.writeText(predictionText)
        .then(() => {
          message.success('Prediction copied to clipboard!');
        })
        .catch(err => {
          console.error('Failed to copy text: ', err);
          message.error('Failed to copy prediction.');
        });
    }
  };

  const handleShare = async () => {
    if (predictionResult) {
       const predictionText = `${predictionResult.model_alias} predicts: ${predictionResult.predicted_winner} to win (Confidence: ${(predictionResult.confidence * 100).toFixed(1)}%)${predictionResult.margin ? ` | Margin: ${predictionResult.margin}` : ''}`;
      const shareData = {
        title: 'NRL Prediction',
        text: predictionText,
        url: window.location.href, // Or a specific URL if applicable
      };
      try {
        if (navigator.share) {
          await navigator.share(shareData);
          console.log('Prediction shared successfully');
        } else {
          // Fallback for browsers that don't support navigator.share
          handleCopy(); // Copy to clipboard as a fallback
          message.info('Web Share API not supported. Prediction copied instead.');
        }
      } catch (err) {
        console.error('Error sharing prediction:', err);
        // Don't show error message if user cancels share dialog
        if (!err?.toString().includes('AbortError')) {
            message.error('Failed to share prediction.');
        }
      }
    }
  };

  const handleRatingSubmit = async (value: number) => {
    if (!currentUser) {
      message.error('You must be logged in to rate predictions.');
      return;
    }
    if (!predictionResult?.prediction_id) {
      message.error('Cannot submit rating: Prediction ID is missing.');
      console.error("Missing prediction_id in predictionResult:", predictionResult);
      return;
    }

    setRatingValue(value); // Update visual state immediately
    setIsRatingLoading(true);

    try {
      const idToken = await currentUser.getIdToken();
      await submitPredictionRating(predictionResult.prediction_id, value, idToken);
      message.success('Rating submitted successfully!');
      setRatingSubmitted(true); // Prevent re-rating
    } catch (err: any) {
      console.error("Failed to submit rating:", err);
      message.error(err.message || 'Failed to submit rating.');
      // Optionally reset visual state if submission fails and retry is desired
      // setRatingValue(0);
    } finally {
      setIsRatingLoading(false);
    }
  };


  if (loading) {
    return <Spin tip="Generating Prediction..." size="large" style={{ display: 'block', marginTop: 20 }} />;
  }

  if (error) {
    return <Alert message="Prediction Error" description={error} type="error" showIcon style={{ marginTop: 20 }} />;
  }

  if (!predictionResult) {
    return null; // Don't render anything if there's no result yet (and not loading/error)
  }

  // Add logging to inspect the value
  console.log("PredictionOutput received predictionResult:", predictionResult);
  console.log("Value of predictionResult.confidence:", predictionResult.confidence);
  console.log("Type of predictionResult.confidence:", typeof predictionResult.confidence);


  // Format the result for display
  // Ensure confidence is treated as a number before calculation
  const confidenceValue = Number(predictionResult.confidence);
  const confidencePercent = !isNaN(confidenceValue) ? (confidenceValue * 100).toFixed(1) : 'N/A';


  return (
    // Use the custom card style defined in App.css
    <div className="card" style={{ marginTop: 20 }}>
      {/* Replicate title functionality */}
      <Title level={3} style={{ marginTop: 0, marginBottom: 16 }}>Prediction Result ({predictionResult.model_alias})</Title>

      <Title level={4}>{predictionResult.predicted_winner}</Title>
      <Paragraph>
        <Text strong>Confidence:</Text> {confidencePercent}%
      </Paragraph>
      {predictionResult.margin !== undefined && ( // Only show margin if it exists
         <Paragraph>
           <Text strong>Predicted Margin:</Text> {predictionResult.margin}
         </Paragraph>
      )}
       <Paragraph style={{ fontStyle: 'italic', color: 'grey', fontSize: 'small' }}>
         Remember: Predictions are based on historical data and models have limitations. Always gamble responsibly.
       </Paragraph>
      <Space style={{ marginTop: 16 }}>
        <Button icon={<CopyOutlined />} onClick={handleCopy}>Copy</Button>
        {/* Explicit check for navigator.share */}
        {typeof navigator.share !== 'undefined' && <Button icon={<ShareAltOutlined />} onClick={handleShare}>Share</Button>}
      </Space>
      <Divider />
      <Space direction="vertical" align="start">
         <Text>Rate this prediction's quality:</Text>
         {predictionResult?.prediction_id && predictionResult.prediction_id > 0 ? (
           <>
             <Rate
               allowHalf={false}
               value={ratingValue}
               onChange={handleRatingSubmit}
               disabled={isRatingLoading || ratingSubmitted || !currentUser}
               tooltips={['Terrible', 'Bad', 'Okay', 'Good', 'Great']}
             />
             {ratingSubmitted && <Text type="success">Thanks for your feedback!</Text>}
           </>
         ) : (
           <Text type="secondary">Rating unavailable for this prediction.</Text>
         )}
      </Space>
    </div> // Close the custom card div
  );
};

export default PredictionOutput;

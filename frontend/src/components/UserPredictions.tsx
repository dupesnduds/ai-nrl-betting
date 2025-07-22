import React, { useState, useEffect } from 'react';
import { List, Typography, Spin, Alert, Button, Modal, Form, Select, InputNumber, message, Rate, Space } from 'antd'; // Added components
import { EditOutlined } from '@ant-design/icons'; // Added icon
import { useAuth } from '../contexts/AuthContext';
import { getUserPredictions, submitActualResult } from '../services/predictionAPI'; // Added submitActualResult
import { PredictionResult } from '../types';

const { Title, Text } = Typography; // Added Text
const { Option } = Select;

const UserPredictions: React.FC = () => {
  const { currentUser } = useAuth();
  const [predictions, setPredictions] = useState<PredictionResult[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [selectedPrediction, setSelectedPrediction] = useState<PredictionResult | null>(null);
  const [isSubmittingResult, setIsSubmittingResult] = useState(false);
  const [form] = Form.useForm(); // Form instance for the modal

  const fetchPredictions = async () => { // Extracted fetch logic into a function
    if (!currentUser) {
      setError("Please log in to view your predictions.");
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const token = await currentUser.getIdToken();
      const userPreds = await getUserPredictions(token);
      // Sort predictions by timestamp descending (newest first)
      userPreds.sort((a, b) => {
        const dateA = a.prediction_timestamp ? new Date(a.prediction_timestamp).getTime() : 0;
        const dateB = b.prediction_timestamp ? new Date(b.prediction_timestamp).getTime() : 0;
        return dateB - dateA;
      });
      setPredictions(userPreds);
    } catch (err: any) {
      console.error("Error fetching user predictions:", err);
      setError(err.message || "Failed to load your predictions.");
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    const fetchPredictions = async () => {
      if (!currentUser) {
        setError("Please log in to view your predictions.");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const token = await currentUser.getIdToken();
        const userPreds = await getUserPredictions(token);
        setPredictions(userPreds);
      } catch (err: any) {
        console.error("Error fetching user predictions:", err);
        setError(err.message || "Failed to load your predictions.");
      } finally {
        setLoading(false);
      }
    };

    fetchPredictions();
  }, [currentUser]); // Re-fetch if user changes

  const showAddResultModal = (prediction: PredictionResult) => {
    setSelectedPrediction(prediction);
    form.resetFields(); // Reset form fields when opening
    setIsModalVisible(true);
  };

  const handleModalCancel = () => {
    setIsModalVisible(false);
    setSelectedPrediction(null);
  };

  const handleResultSubmit = async (values: { actual_winner: string; actual_margin: number }) => {
    if (!currentUser || !selectedPrediction?.prediction_id) {
      message.error("Cannot submit result. User or Prediction ID missing.");
      return;
    }

    setIsSubmittingResult(true);
    try {
      const idToken = await currentUser.getIdToken();
      await submitActualResult(
        selectedPrediction.prediction_id,
        values.actual_winner,
        values.actual_margin,
        idToken
      );
      message.success('Actual result submitted successfully!');

      // Update the local state to reflect the change without re-fetching
      setPredictions(prevPredictions =>
        prevPredictions.map(p =>
          p.prediction_id === selectedPrediction.prediction_id
            ? { ...p, actual_winner: values.actual_winner, actual_margin: values.actual_margin }
            : p
        )
      );

      setIsModalVisible(false);
      setSelectedPrediction(null);
    } catch (err: any) {
      console.error("Error submitting actual result:", err);
      message.error(err.message || "Failed to submit actual result.");
    } finally {
      setIsSubmittingResult(false);
    }
  };


  return (
    <div>
      <Title level={4}>My Past Predictions</Title>
      {loading && <Spin tip="Loading predictions..." />}
      {error && <Alert message="Error" description={error} type="error" showIcon style={{ marginBottom: 16 }} />}
      {!loading && !error && predictions.length === 0 && (
        <p>You haven't made any predictions yet.</p>
      )}
      {!loading && !error && predictions.length > 0 && (
        <List
          itemLayout="horizontal"
          dataSource={predictions}
          renderItem={(item) => {
            const title = `${item.home_team_name || 'N/A'} vs ${item.away_team_name || 'N/A'} (${item.match_date || 'N/A'})`;
            const predictionDetails = `Predicted: ${item.predicted_winner || 'N/A'} (Confidence: ${(item.confidence * 100).toFixed(1)}%) | Model: ${item.model_alias}`;
            const savedTime = `Saved: ${item.prediction_timestamp ? new Date(item.prediction_timestamp).toLocaleString() : 'N/A'}`;

            // Wrap the content of each list item in a card
            return (
              <List.Item style={{ padding: 0, border: 'none' }}> {/* Remove default List.Item padding/border */}
                <div className="card" style={{ width: '100%', marginBottom: '15px' }}> {/* Apply card style */}
                  <List.Item.Meta
                    title={title}
                    description={
                      <>
                        <div>{predictionDetails}</div>
                        {item.user_rating !== undefined && item.user_rating !== null && (
                          <div style={{ marginTop: '4px' }}>
                            <Space align="center">
                              <Text>Your Rating:</Text>
                              <Rate disabled allowHalf={false} value={item.user_rating} style={{ fontSize: '16px' }} />
                            </Space>
                          </div>
                        )}
                        <div style={{ color: 'grey', fontSize: 'small', marginTop: '4px' }}>{savedTime}</div>
                      </>
                    }
                  />
                  {/* Actions moved inside the card */}
                  <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #f0f0f0' }}>
                    {item.actual_winner
                      ? <Text strong>Result: {item.actual_winner} by {item.actual_margin}</Text>
                      : <Button
                          icon={<EditOutlined />}
                          onClick={() => showAddResultModal(item)}
                          disabled={!currentUser} // Disable if not logged in
                        >
                          Add Result
                        </Button>
                    }
                  </div>
                </div>
              </List.Item>
            );
            /* Original structure commented out for reference
              <List.Item
                actions={[
                  // Show result if available, otherwise show button to add result
                  item.actual_winner
                    ? <Text strong>Result: {item.actual_winner} by {item.actual_margin}</Text>
                    : <Button
                        icon={<EditOutlined />}
                        onClick={() => showAddResultModal(item)}
                        disabled={!currentUser} // Disable if not logged in
                        >
                          Add Result
                        </Button>
                ]}
              >
                <List.Item.Meta
                  title={title}
                  description={
                    <>
                      <div>{predictionDetails}</div>
                      {item.user_rating !== undefined && item.user_rating !== null && (
                        <div style={{ marginTop: '4px' }}>
                          <Space align="center">
                            <Text>Your Rating:</Text>
                            <Rate disabled allowHalf={false} value={item.user_rating} style={{ fontSize: '16px' }} />
                          </Space>
                        </div>
                      )}
                      <div style={{ color: 'grey', fontSize: 'small', marginTop: '4px' }}>{savedTime}</div>
                    </>
                  }
                />
              </List.Item>
            */
          }}
        />
      )}

      {/* Modal for Adding Actual Result */}
      <Modal
        title={`Record Actual Result for ${selectedPrediction?.home_team_name} vs ${selectedPrediction?.away_team_name}`}
        open={isModalVisible}
        onCancel={handleModalCancel}
        footer={null} // Footer handled by Form buttons
        destroyOnClose // Reset form state when modal is closed
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleResultSubmit}
          initialValues={{ actual_margin: 0 }} // Default margin to 0
        >
          <Form.Item
            label="Actual Winner"
            name="actual_winner"
            rules={[{ required: true, message: 'Please select the actual winner!' }]}
          >
            <Select placeholder="Select Winner">
              {/* Populate options based on the selected prediction */}
              {selectedPrediction?.home_team_name && <Option value={selectedPrediction.home_team_name}>{selectedPrediction.home_team_name}</Option>}
              {selectedPrediction?.away_team_name && <Option value={selectedPrediction.away_team_name}>{selectedPrediction.away_team_name}</Option>}
              <Option value="Draw">Draw</Option>
            </Select>
          </Form.Item>

          <Form.Item
            label="Actual Margin"
            name="actual_margin"
            rules={[{ required: true, message: 'Please enter the actual margin!' }]}
          >
            <InputNumber min={0} style={{ width: '100%' }} placeholder="Enter margin (e.g., 12)" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button onClick={handleModalCancel} disabled={isSubmittingResult}>
                Cancel
              </Button>
              <Button type="primary" htmlType="submit" loading={isSubmittingResult}>
                Save Result
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default UserPredictions;

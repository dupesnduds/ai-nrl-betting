import React, { useState, useEffect } from 'react'; // Added useEffect
import { Form, Select, InputNumber, DatePicker, Radio, Button, Space, Tag, Tooltip, Modal } from 'antd'; // Added Tag, Tooltip, Modal
import { LockOutlined } from '@ant-design/icons'; // Added LockOutlined
import dayjs from 'dayjs'; // For DatePicker default value and formatting
import { PredictionFormData, PredictionRequestPayload } from '../types';
import { PREDICTION_MODELS, DEFAULT_MODEL_ALIAS } from '../config/models';
import { useAuth } from '../contexts/AuthContext';
import teamsData from '../data/teams.json'; // Import the JSON data directly

const { Option } = Select;

interface PredictionFormProps {
  // Update onSubmit to accept the optional idToken
  onSubmit: (payload: PredictionRequestPayload, modelAlias: string, idToken: string | null) => void;
  isLoading: boolean;
}

const PredictionForm: React.FC<PredictionFormProps> = ({ onSubmit, isLoading }) => {
  const [form] = Form.useForm<PredictionFormData>();
  const { currentUser } = useAuth(); // Get currentUser from context
  const [isUpgradeModalVisible, setIsUpgradeModalVisible] = useState(false);
  const [modalModelAlias, setModalModelAlias] = useState('');
  const [allowedModes, setAllowedModes] = useState<string[]>(['Quick Pick']); // Default to Quick Pick only

    useEffect(() => {
    const fetchAllowedModes = async () => {
      try {
        const token = currentUser ? await currentUser.getIdToken() : null;
        const response = await fetch('http://localhost:8007/users/me/modes', {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (response.ok) {
          const modes = await response.json();
          setAllowedModes(modes);
        } else if (response.status === 403) {
          console.warn('User not authorized for premium modes (403). Defaulting to free tier.');
          setAllowedModes(['Quick Pick']);
        } else {
          console.error('Failed to fetch allowed modes, status:', response.status);
          setAllowedModes(['Quick Pick']);
        }
      } catch (error) {
        console.error('Error fetching allowed modes:', error);
        setAllowedModes(['Quick Pick']);
      }
    };

    fetchAllowedModes();
  }, [currentUser]);


  // Watch selected teams to disable selection in the other dropdown
  const homeTeamValue = Form.useWatch('homeTeam', form);
  const awayTeamValue = Form.useWatch('awayTeam', form);

  // Removed useEffect for fetching teams

  const handleFormSubmit = async (values: PredictionFormData) => { // Make async
    // Basic validation
    if (!values.homeTeam || !values.awayTeam || !values.matchDate) {
      // Antd Form validation should handle this, but good to double-check
      console.error("Form validation failed - missing required fields.");
      return;
    }

    // Determine the model alias - Restore check even if UI is hidden for now
    // Use selected value if available, otherwise default. Paid status check removed temporarily.
    const modelAlias = values.selectedModelAlias || DEFAULT_MODEL_ALIAS;

    // Construct the payload for the API
    const payload: PredictionRequestPayload = {
      team_a: values.homeTeam,
      team_b: values.awayTeam,
      match_date_str: dayjs(values.matchDate).format('YYYY-MM-DD'), // Format date
      // Only include odds if they are provided, valid numbers, AND the model is not 'Deep Dive'
      ...(modelAlias !== 'Deep Dive' && values.homeOdds != null && !isNaN(values.homeOdds) && { odd_a: values.homeOdds }),
      ...(modelAlias !== 'Deep Dive' && values.awayOdds != null && !isNaN(values.awayOdds) && { odd_b: values.awayOdds }),
      odds_home_win: values.homeOdds ?? null,
      odds_away_win: values.awayOdds ?? null,
    };

    // Get ID token if user is logged in
    let idToken: string | null = null;
    if (currentUser) {
      try {
        idToken = await currentUser.getIdToken();
        console.log("Retrieved ID token for API call.");
      } catch (error) {
        console.error("Error getting ID token:", error);
        // Decide how to handle token error - maybe show an alert?
        // For now, proceed without token, but log the error.
      }
    }

    // Pass payload, modelAlias, and the token (or null) to the onSubmit handler
    // The parent component (App.tsx) will pass the token to getPrediction
    onSubmit(payload, modelAlias, idToken);
  };

  const showUpgradeModal = (alias: string) => {
    setModalModelAlias(alias);
    setIsUpgradeModalVisible(true);
  };

  const handleModalCancel = () => {
    setIsUpgradeModalVisible(false);
  };


  return (
    // Wrap the entire form in the card style
    <div className="card">
      <Form
        form={form}
        // layout="vertical" // Let the card handle overall layout
        onFinish={handleFormSubmit}
        initialValues={{
          matchDate: dayjs(), // Default to today
          selectedModelAlias: DEFAULT_MODEL_ALIAS,
        }}
        disabled={isLoading} // Only disable based on submission loading state
      >
        <Form.Item
          label="Home Team"
          name="homeTeam"
          rules={[{ required: true, message: 'Please select the home team!' }]}
        >
          <Select placeholder="Select Home Team" showSearch optionFilterProp="children">
            {/* Use imported teamsData */}
            {teamsData.map(team => (
              <Option key={team.id} value={team.name} disabled={team.name === awayTeamValue}>
                {team.name}
              </Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item
          label="Away Team"
          name="awayTeam"
          rules={[{ required: true, message: 'Please select the away team!' }]}
        >
          <Select placeholder="Select Away Team" showSearch optionFilterProp="children">
            {/* Use imported teamsData */}
            {teamsData.map(team => (
              <Option key={team.id} value={team.name} disabled={team.name === homeTeamValue}>
                {team.name}
              </Option>
            ))}
          </Select>
        </Form.Item>

        <Space wrap>
            <Form.Item label="Home Odds (Optional)" name="homeOdds">
            <InputNumber
              min={0}
              step={0.01}
              style={{ width: '100%' }}
              placeholder="e.g., 1.90"
              keyboard={true}
              controls={true}
              stringMode
            />
            </Form.Item>

            <Form.Item label="Away Odds (Optional)" name="awayOdds">
            <InputNumber
              min={0}
              step={0.01}
              style={{ width: '100%' }}
              placeholder="e.g., 2.10"
              keyboard={true}
              controls={true}
              stringMode
            />
            </Form.Item>
        </Space>


        <Form.Item
          label="Match Date"
          name="matchDate"
          rules={[{ required: true, message: 'Please select the match date!' }]}
        >
          <DatePicker style={{ width: '100%' }} format="YYYY-MM-DD" />
        </Form.Item>

        {/* Model Selection UI */}
        <Form.Item label="Select Prediction Type" name="selectedModelAlias">
          <Radio.Group style={{ width: '100%' }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              {PREDICTION_MODELS.map(model => {
                const isAllowed = allowedModes.includes(model.alias);
                const isPremium = model.tier === 'premium';
                const isDisabled = !isAllowed;

                return (
                  <Tooltip key={model.id} title={model.description} placement="right">
                    <div
                      onClick={() => {
                        if (isDisabled) {
                          showUpgradeModal(model.alias);
                        }
                      }}
                      style={{ display: 'inline-block', width: '100%', cursor: isDisabled ? 'not-allowed' : 'pointer' }}
                    >
                      <Radio.Button
                        value={model.alias}
                        disabled={isDisabled}
                        style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
                      >
                        <Space>
                          <span>{model.alias}</span>
                          {isPremium && <Tag color="gold">Premium</Tag>}
                        </Space>
                        {isDisabled && <LockOutlined />}
                      </Radio.Button>
                    </div>
                  </Tooltip>
                );
              })}
            </Space>
          </Radio.Group>
        </Form.Item>


        <Form.Item>
          <Button type="primary" htmlType="submit" loading={isLoading}>
            Get Prediction
          </Button>
        </Form.Item>
      </Form>

      {/* Upgrade Modal */}
      <Modal
        title="Upgrade Required"
        open={isUpgradeModalVisible}
        onCancel={handleModalCancel}
        footer={[
          <Button key="back" onClick={handleModalCancel}>
            Close
          </Button>,
        ]}
      >
        <div style={{ padding: "10px" }}>
          <h3 style={{ marginBottom: "10px" }}>
            Upgrade to Premium to access the <strong>{modalModelAlias}</strong> model and other advanced features.
          </h3>

          <div style={{ marginBottom: "20px", fontSize: "0.9em", color: "#555" }}>
            Unlock deeper insights, advanced analytics, and more.
          </div>

          <h4>Have a coupon code?</h4>
          <div style={{ display: "flex", gap: "8px", marginBottom: "20px" }}>
            <input
              type="text"
              placeholder="Enter coupon code"
              id="couponInputUpgrade"
              style={{ flex: 1, padding: "6px 8px", borderRadius: "4px", border: "1px solid #ccc" }}
            />
            <Button
              onClick={async () => {
                const couponCode = (document.getElementById("couponInputUpgrade") as HTMLInputElement).value;
                const firebaseUid = localStorage.getItem("firebase_uid") || ""; // Assumes UID stored in localStorage
                if (!firebaseUid) {
                  alert("User ID not found. Please log in.");
                  return;
                }
                const res = await fetch("http://localhost:8007/purchase/coupon", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ firebase_uid: firebaseUid, coupon_code: couponCode }),
                });
                if (res.ok) {
                  alert("Coupon redeemed! You now have Premium access.");
                  window.location.reload();
                } else {
                  const data = await res.json();
                  alert("Coupon error: " + (data.detail || "Invalid coupon"));
                }
              }}
            >
              Redeem
            </Button>
          </div>

          <div style={{ textAlign: "center", margin: "20px 0" }}>
            <span style={{ color: "#999" }}>OR</span>
          </div>

          <h4>Subscribe with your card</h4>
          <Button
            type="primary"
            block
            size="large"
            style={{ marginTop: "10px" }}
            onClick={async () => {
              const priceId = "price_premium"; // Replace with real price ID
              const res = await fetch("/api/stripe/create-checkout-session", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ priceId }),
              });
              const data = await res.json();
              if (data.checkoutUrl) {
                window.location.href = data.checkoutUrl;
              } else {
                alert("Error creating checkout session: " + (data.error || "Unknown error"));
              }
            }}
          >
            Upgrade with Card
          </Button>
        </div>
      </Modal>
    </div> // Close the card div
  );
};

export default PredictionForm;

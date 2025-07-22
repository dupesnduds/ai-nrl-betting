import React, { useEffect, useState } from 'react';
import { Button, Input, message, Card, Typography } from 'antd';
import axios from 'axios';

const { Title, Paragraph } = Typography;

const PURCHASE_API = 'http://localhost:8010/purchase';

const PurchasePanel: React.FC<{ firebaseUid?: string; sessionId?: string }> = ({ firebaseUid, sessionId }) => {
  const [status, setStatus] = useState<{ has_access: boolean; tier?: string; expires_at?: string }>({ has_access: false });
  const [couponCode, setCouponCode] = useState('');
  const [oneTimeCode, setOneTimeCode] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchStatus = async () => {
    try {
      const params: any = {};
      if (firebaseUid) params.firebase_uid = firebaseUid;
      if (sessionId) params.session_id = sessionId;
      const res = await axios.get(PURCHASE_API + '/status', { params });
      setStatus(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, [firebaseUid, sessionId]);

  const handleCouponRedeem = async () => {
    setLoading(true);
    try {
      const res = await axios.post(PURCHASE_API + '/coupon', {
        firebase_uid: firebaseUid,
        coupon_code: couponCode,
      });
      message.success('Coupon redeemed! Access granted.');
      fetchStatus();
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Coupon redemption failed');
    } finally {
      setLoading(false);
    }
  };

  const handleOneTimeRedeem = async () => {
    setLoading(true);
    try {
      const res = await axios.post(PURCHASE_API + '/one-time', {
        session_id: sessionId,
        one_time_code: oneTimeCode,
      });
      message.success('One-time code redeemed! Access granted.');
      fetchStatus();
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'One-time code redemption failed');
    } finally {
      setLoading(false);
    }
  };

  const handleStripePurchase = async () => {
    message.info('Stripe payment flow not yet implemented');
    // TODO: Integrate Stripe.js or redirect to checkout
  };

  return (
    <Card title="Premium Access">
      {status.has_access ? (
        <>
          <Title level={4}>You have premium access</Title>
          <Paragraph>Tier: {status.tier}</Paragraph>
          <Paragraph>Expires at: {status.expires_at}</Paragraph>
        </>
      ) : (
        <>
          <Title level={5}>Purchase Premium Access</Title>
          <Button type="primary" onClick={handleStripePurchase} loading={loading} style={{ marginBottom: 16 }}>
            Purchase with Stripe
          </Button>

          <Title level={5}>Or Redeem Coupon</Title>
          <Input
            placeholder="Enter coupon code"
            value={couponCode}
            onChange={(e) => setCouponCode(e.target.value)}
            style={{ marginBottom: 8 }}
          />
          <Button onClick={handleCouponRedeem} loading={loading} style={{ marginBottom: 16 }}>
            Redeem Coupon
          </Button>

          <Title level={5}>Or Use One-Time Code</Title>
          <Input
            placeholder="Enter one-time code"
            value={oneTimeCode}
            onChange={(e) => setOneTimeCode(e.target.value)}
            style={{ marginBottom: 8 }}
          />
          <Button onClick={handleOneTimeRedeem} loading={loading}>
            Redeem One-Time Code
          </Button>
        </>
      )}
    </Card>
  );
};

export default PurchasePanel;

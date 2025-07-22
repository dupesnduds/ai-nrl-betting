import React, { useEffect, useState } from "react";

interface Product {
  id: string;
  name: string;
  price: string;
}

const Subscription: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [entitlements, setEntitlements] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch("/api/stripe/products")
      .then((res) => res.json())
      .then(setProducts);

    const fetchEntitlements = () => {
      fetch("/api/stripe/entitlements")
        .then((res) => res.json())
        .then((data) => setEntitlements(data.entitlements));
    };

    fetchEntitlements();

    const interval = setInterval(fetchEntitlements, 30000); // Poll every 30 seconds

    return () => clearInterval(interval);
  }, []);

  const handleSubscribe = async (priceId: string) => {
    setLoading(true);
    const res = await fetch("/api/stripe/create-checkout-session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ priceId }),
    });
    const data = await res.json();
    window.location.href = data.checkoutUrl;
  };

  const handleManageSubscription = async () => {
    setLoading(true);
    const res = await fetch("/api/stripe/customer-portal", {
      method: "POST",
    });
    const data = await res.json();
    window.location.href = data.portalUrl;
  };

  return (
    <div>
      <h2>Subscription Plans</h2>

      {/* Embed Stripe Pricing Table */}
      {/* Replace 'prctbl_xxx' and 'pk_test_xxx' with real IDs/keys */}
      {/* 
      <stripe-pricing-table
        pricing-table-id="prctbl_xxx"
        publishable-key="pk_test_xxx"
      ></stripe-pricing-table>
      */}

      <button onClick={handleManageSubscription} disabled={loading}>
        Manage Subscription
      </button>

      <h3>Current Entitlements</h3>
      <ul>
        {entitlements.map((ent) => (
          <li key={ent}>{ent}</li>
        ))}
      </ul>

      <h3>Trial Status</h3>
      {/* TODO: Replace with real trial status */}
      <p>Trial active until 2025-09-01 (placeholder)</p>

      <h3>Billing Info</h3>
      {/* TODO: Replace with real billing info */}
      <p>Next payment: $10 on 2025-09-01 (placeholder)</p>
      <p>Status: Active (placeholder)</p>

      <h3>Upgrade Options</h3>
      {/* TODO: Replace with real upgrade options */}
      <p>Upgrade to Premium for more features (placeholder)</p>

      <div style={{ border: "1px solid #ccc", padding: "1em", marginTop: "1em" }}>
        <h4>Upgrade to Premium</h4>

        {/* Coupon Redemption */}
        <div>
          <p>Have a coupon code?</p>
          <input
            type="text"
            placeholder="Enter coupon code"
            id="couponInput"
          />
          <button
            onClick={async () => {
              const couponCode = (document.getElementById("couponInput") as HTMLInputElement).value;
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
            Redeem Coupon
          </button>
        </div>

        <hr />

        {/* Stripe Payment */}
        <div>
          <p>Or subscribe with your card:</p>
          <button
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
            Subscribe with Card
          </button>
        </div>
      </div>
    </div>
  );
};

export default Subscription;

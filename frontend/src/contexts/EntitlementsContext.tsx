import React, { createContext, useContext, useEffect, useState } from "react";

interface EntitlementsContextType {
  entitlements: string[];
  loading: boolean;
}

const EntitlementsContext = createContext<EntitlementsContextType>({
  entitlements: [],
  loading: true,
});

export const useEntitlements = () => useContext(EntitlementsContext);

export const EntitlementsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [entitlements, setEntitlements] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchEntitlements = () => {
      fetch("/api/stripe/entitlements")
        .then((res) => res.json())
        .then((data) => {
          setEntitlements(data.entitlements);
          setLoading(false);
        });
    };

    fetchEntitlements();

    const interval = setInterval(fetchEntitlements, 30000); // Poll every 30 seconds

    return () => clearInterval(interval);
  }, []);

  return (
    <EntitlementsContext.Provider value={{ entitlements, loading }}>
      {children}
    </EntitlementsContext.Provider>
  );
};

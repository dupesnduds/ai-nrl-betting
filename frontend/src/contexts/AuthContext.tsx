// frontend-react-ts/src/contexts/AuthContext.tsx
import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from 'react';
import { User, onAuthStateChanged } from 'firebase/auth';
import { auth } from '../config/firebaseConfig'; // Import initialized auth

// Define the shape of the context data
interface AuthContextType {
  currentUser: User | null;
  loading: boolean;
  // We can add login/logout functions here later
}

// Create the context with a default value (or null)
// Using '!' asserts that the context will be provided, handle with care or provide default implementation
const AuthContext = createContext<AuthContextType>(null!);

// Custom hook to use the auth context easily
export function useAuth() {
  return useContext(AuthContext);
}

// Define props for the provider component
interface AuthProviderProps {
  children: ReactNode;
}

// Create the provider component
export function AuthProvider({ children }: AuthProviderProps) {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true); // Start loading until auth state is confirmed

  useEffect(() => {
    // Subscribe to Firebase auth state changes
    // onAuthStateChanged returns an unsubscribe function
    const unsubscribe = onAuthStateChanged(
      auth,
      (user) => {
        console.log('Auth State Changed:', user ? `User UID: ${user.uid}` : 'No user');
        setCurrentUser(user); // Set user (null if logged out)
        setLoading(false); // Auth state confirmed, stop loading
      },
      (error) => {
        // Handle potential errors during subscription
        console.error('Error subscribing to auth state changes:', error);
        setCurrentUser(null);
        setLoading(false);
      }
    );

    // Cleanup subscription on unmount
    return unsubscribe;
  }, []); // Empty dependency array ensures this runs only once on mount

  // Value provided by the context
  const value = {
    currentUser,
    loading,
    // Add login/logout functions here later
  };

  // Render children only when not loading to prevent rendering protected routes prematurely
  // Or, render children immediately and let components handle the loading state
  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
      {/* Or simply: {children} and handle loading in consuming components */}
    </AuthContext.Provider>
  );
}

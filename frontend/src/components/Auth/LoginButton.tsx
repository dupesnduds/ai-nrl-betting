// frontend-react-ts/src/components/Auth/LoginButton.tsx
import React from 'react';
import { signInWithPopup } from 'firebase/auth';
import { auth, googleProvider } from '../../config/firebaseConfig';
// import { useAuth } from '../../contexts/AuthContext'; // Optional: use context if needed later

const LoginButton: React.FC = () => {
  // const { currentUser } = useAuth(); // Get user state if needed

  const handleGoogleSignIn = async () => {
    try {
      console.log('Attempting Google Sign-In...');
      const result = await signInWithPopup(auth, googleProvider);
      const user = result.user;
      console.log('Sign-in successful:', user.uid);

      // Store UID in localStorage for upgrade flows
      localStorage.setItem("firebase_uid", user.uid);

      // --- Send ID token to backend ---
      if (user) {
        try {
          const idToken = await user.getIdToken();
          console.log('Sending ID token to backend...');
          const response = await fetch('http://localhost:8007/users/me', { // Ensure this matches your User Service port
            method: 'GET', // Changed from POST to match backend @app.get
            headers: {
              // 'Content-Type': 'application/json', // Not needed for GET typically
              Authorization: `Bearer ${idToken}`,
            },
            // body: JSON.stringify({}), // Include body if your endpoint expects one
          });

          if (!response.ok) {
            const errorData = await response.text(); // Or response.json() if backend sends JSON error
            throw new Error(`Backend verification failed: ${response.status} ${errorData}`);
          }

          const backendUserData = await response.json();
          console.log('Backend verification successful:', backendUserData);
          // Optionally update local state or context with backendUserData if needed

        } catch (backendError) {
          console.error('Error sending token to backend:', backendError);
          // Handle backend error (e.g., show message to user)
          // Consider logging out the user locally if backend verification fails critically
          // await auth.signOut(); // Example: Force sign out on backend failure
        }
      }
      // --- End token sending ---

    } catch (error) {
      console.error('Error during Google Sign-In:', error);
      // Handle specific errors (e.g., popup closed, network error)
    }
  };

  // Optionally, hide button if user is already logged in
  // if (currentUser) {
  //   return null;
  // }

  return (
    <button onClick={handleGoogleSignIn} style={buttonStyle}>
      Sign in with Google
    </button>
  );
};

// Basic styling (can be moved to CSS)
const buttonStyle: React.CSSProperties = {
  padding: '10px 15px',
  backgroundColor: '#4285F4', // Google blue
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '1rem',
};

export default LoginButton;

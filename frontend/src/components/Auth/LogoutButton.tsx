// frontend-react-ts/src/components/Auth/LogoutButton.tsx
import React from 'react';
import { signOut } from 'firebase/auth';
import { auth } from '../../config/firebaseConfig';
// import { useAuth } from '../../contexts/AuthContext'; // Optional: use context if needed

const LogoutButton: React.FC = () => {
  // const { currentUser } = useAuth(); // Get user state if needed

  const handleSignOut = async () => {
    try {
      console.log('Attempting Sign Out...');
      await signOut(auth);
      // This will trigger the onAuthStateChanged listener in AuthContext
      console.log('Sign-out successful.');
    } catch (error) {
      console.error('Error during Sign Out:', error);
    }
  };

  // Optionally, only show button if user is logged in
  // if (!currentUser) {
  //   return null;
  // }

  return (
    <button onClick={handleSignOut} style={buttonStyle}>
      Sign Out
    </button>
  );
};

// Basic styling (can be moved to CSS)
const buttonStyle: React.CSSProperties = {
  padding: '10px 15px',
  backgroundColor: '#DB4437', // Google red
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '1rem',
  marginLeft: '10px', // Add some space if next to login button
};

export default LogoutButton;

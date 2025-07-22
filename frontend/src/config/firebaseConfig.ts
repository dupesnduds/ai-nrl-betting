// frontend-react-ts/src/config/firebaseConfig.ts
import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider } from 'firebase/auth';
// import { getAnalytics } from "firebase/analytics"; // Optional: if you use Analytics

// Actual Firebase project configuration:
const firebaseConfig = {
    apiKey: "AIzaSyBkD_otF5qHZxS6eLzLtjefQHYdEynW2oM",
    authDomain: "tumunu-36598.firebaseapp.com",
    projectId: "tumunu-36598",
    storageBucket: "tumunu-36598.firebasestorage.app",
    messagingSenderId: "412273316518",
    appId: "1:412273316518:web:0b2a0c5ff50d4b27e21a67",
    measurementId: "G-CGSCV1QHGH"
  };

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firebase Authentication and get a reference to the service
export const auth = getAuth(app);

// Initialize Google Auth Provider
export const googleProvider = new GoogleAuthProvider();

// Optional: Initialize Analytics
// export const analytics = getAnalytics(app);

export default app; // Export the initialized app if needed elsewhere

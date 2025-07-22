import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import 'antd/dist/reset.css';
import './index.css'; // Import our custom CSS after Ant Design
import './App.css';
import { useAuth } from './contexts/AuthContext';
// Import view components
import MainPredictionView from './components/MainPredictionView';
import UserPredictions from './components/UserPredictions';
// Import layout components
import Sidebar from './components/Layout/Sidebar';
import Header from './components/Layout/Header';
import MainContent from './components/Layout/MainContent';
import RightPanel from './components/Layout/RightPanel'; // Import RightPanel
import Footer from './components/Layout/Footer';
// Footer is removed in the scaffold example, can be added back if needed
import Subscription from './Subscription';

function AppContent() {
  // currentUser is no longer needed here for routing logic
  // const { currentUser } = useAuth();

  return (
    // Renaming outer div to 'app' to match scaffold CSS
    <div className="app">
      <Header />
      {/* 'layout' div wraps sidebar, main content, and right panel */}
      <div className="layout">
        <Sidebar />
        {/* Routes now define the layout structure, MainContent uses Outlet */}
        <Routes>
           {/* Define a parent route that uses MainContent */}
           <Route element={<MainContent />}>
             {/* Child routes render inside MainContent's Outlet */}
             <Route index element={<MainPredictionView />} />
             <Route path="my-predictions" element={
               <ProtectedRoute>
                 <UserPredictions />
               </ProtectedRoute>
             } />
             {/* Add other child routes here if needed */}
             <Route path="subscription" element={<Subscription />} />
           </Route>
           {/* Add other top-level routes here if needed */}
        </Routes>
      </div>
      {/* Footer restored */}
      <Footer />
    </div>
  );
}

// Helper component for protected routes
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { currentUser, loading } = useAuth();

  if (loading) {
    // Optional: Show a loading spinner while auth state is resolving
    return <div>Loading...</div>;
  }

  return currentUser ? <>{children}</> : <Navigate to="/" replace />;
};


// Wrap AppContent with BrowserRouter
function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}

export default App;

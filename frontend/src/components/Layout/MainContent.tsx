import React from 'react';
import { Outlet } from 'react-router-dom'; // Import Outlet to render nested routes

// Styles for .main and .content-card are in App.css

const MainContent: React.FC = () => {
  return (
    <main className="main">
      <div className="content-card">
        {/* Render the matched child route's element here */}
        <Outlet />
      </div>
    </main>
  );
};

export default MainContent;

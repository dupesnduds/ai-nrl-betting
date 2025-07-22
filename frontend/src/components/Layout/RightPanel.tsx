import React from 'react';
import NRLChat from '../NRLChat';

// Styles for .right-panel are in App.css

const RightPanel: React.FC = () => (
  <aside className="right-panel">
    <h3>NRL Betting Chat</h3>
    <NRLChat />
  </aside>
);

export default RightPanel;

import React from 'react';
import { Space } from 'antd'; // Keep Space for layout if needed inside auth-controls
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Link } from 'react-router-dom';
import LoginButton from '../Auth/LoginButton';
import LogoutButton from '../Auth/LogoutButton';

const Sidebar: React.FC = () => {
  const { currentUser } = useAuth();

  return (
    <aside className="sidebar">
      <div className="sidebar-top">
        <div className="logo">
          <Link to="/" className="header-logo-link">
            <img src="/logo_colour.svg" alt="Outback Oracles logo" className="header-logo" />
          </Link>
        </div>
        <nav>
          <ul>
            <li>
              <NavLink to="/" end className={({ isActive }) => isActive ? 'active' : ''}>
                Predict
              </NavLink>
            </li>
            {currentUser && (
              <li>
                <NavLink to="/my-predictions" className={({ isActive }) => isActive ? 'active' : ''}>
                  My Predictions
                </NavLink>
              </li>
            )}
          </ul>
        </nav>
      </div>
      <div className="sidebar-bottom">
        <div className="auth-controls">
          <Space>
            {currentUser ? (
              <LogoutButton />
            ) : (
              <LoginButton />
            )}
          </Space>
          {currentUser && currentUser.email && (
            <div className="user-email">{currentUser.email}</div>
          )}
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;

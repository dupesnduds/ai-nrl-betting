import React, { useState } from 'react';
import { Space } from 'antd'; // Keep Space for layout if needed inside auth-controls
import { MenuOutlined } from '@ant-design/icons'; // Hamburger icon
import { useAuth } from '../../contexts/AuthContext';
import { Link, NavLink } from 'react-router-dom';
import LoginButton from '../Auth/LoginButton';
import LogoutButton from '../Auth/LogoutButton';
// Styles are now in App.css

const Header: React.FC = () => {
  const { currentUser } = useAuth();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <>
      <header className="header">
        <div className="logo">
          <Link to="/" className="header-logo-link">
            <img src="/logo_colour.svg" alt="Outback Oracles logo" className="header-logo" />
          </Link>
        </div>

        <div className="auth-controls">
          <Space>
            {currentUser ? (
              <>
                <LogoutButton />
              </>
            ) : (
              <LoginButton />
            )}
          </Space>
        </div>

        <button
          className="hamburger-button"
          aria-label="Toggle menu"
          onClick={() => setIsMenuOpen(!isMenuOpen)}
        >
          <MenuOutlined />
        </button>
      </header>

      {isMenuOpen && (
        <div className="mobile-menu-overlay">
          <nav>
            <ul>
              <li>
                <NavLink to="/" onClick={() => setIsMenuOpen(false)}>
                  Predict
                </NavLink>
              </li>
              {currentUser && (
                <li>
                  <NavLink to="/my-predictions" onClick={() => setIsMenuOpen(false)}>
                    My Predictions
                  </NavLink>
                </li>
              )}
              <li>
                <NavLink to="/subscription" onClick={() => setIsMenuOpen(false)}>
                  Subscription
                </NavLink>
              </li>
            </ul>
          </nav>
          <div className="auth-controls" style={{ marginTop: '1rem' }}>
            <Space direction="vertical">
              {currentUser ? (
                <LogoutButton />
              ) : (
                <LoginButton />
              )}
            </Space>
          </div>
        </div>
      )}
    </>
  );
};

export default Header;

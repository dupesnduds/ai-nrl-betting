// src/components/Layout/Footer.tsx
import React from 'react';
import { Link } from 'react-router-dom';

const Footer: React.FC = () => {
  return (
    <footer className="footer">
      <div className="footer-grid">
        <div className="footer-left">
          <ul>
            <li><Link to="/terms">Terms of Use</Link></li>
            <li><Link to="/privacy">Privacy Policy</Link></li>
          </ul>
        </div>
        <div className="footer-center">
          <a href="https://outbackoracle.com" rel="noopener noreferrer" target="_blank">
            <span>© {new Date().getFullYear()} Outback Oracle</span>
            <img alt="Outback Oracle logo" src="/logo_colour.svg" style={{ height: '24px', marginLeft: '8px' }} />
          </a>
        </div>
        <div className="footer-right">
          <ul>
            <li><Link to="/careers">Careers</Link></li>
            <li><a href="https://nationalrugbyleague.atlassian.net/wiki/spaces/NKB/overview">Help</a></li>
            <li><Link to="/contact">Contact Us</Link></li>
            <li><Link to="/advertise">Advertise With Us</Link></li>
          </ul>
        </div>
      </div>
    </footer>
  );
};

export default Footer;

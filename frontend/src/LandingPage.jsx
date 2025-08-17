import React from 'react';
import GoogleSignIn from './auth/GoogleSignIn';
import './LandingPage.css';

export default function LandingPage({ onAuth }) {
  return (
    <div className="landing-container">
      <div className="landing-header">
        <div className="brand-name">MediMind</div>
      </div>
      <div className="landing-content">
                <h2 className="tagline">Smart retrieval — the right answer from the right place.</h2>
        <h1>MediMind</h1>
        <p>Smart, medical-focused brainpower.</p>
        <div id="google-signin-button">
          <GoogleSignIn onAuth={onAuth} />
        </div>
      </div>
      <div className="landing-footer">
        <p>Powered by Advanced AI | Secure & Private</p>
      </div>
    </div>
  );
}

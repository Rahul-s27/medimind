import { useEffect } from 'react';

export default function GoogleSignIn({ onAuth }) {
  useEffect(() => {
    /* global google */
    if (window.google) {
      window.google.accounts.id.initialize({
        client_id: '942827189906-i4pk9ltfm0fmvgu4p96qokkgerveht4f.apps.googleusercontent.com',
        callback: async (response) => {
          // Send ID token to backend for verification
          const res = await fetch('https://medimind-96a3.onrender.com/auth/verify', {

            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_token: response.credential })
          });
          if (res.ok) {
            const data = await res.json();
            onAuth(data.token, data.user);
          } else {
            alert('Authentication failed');
          }
        },
      });
      window.google.accounts.id.renderButton(
        document.getElementById('google-btn'),
        { theme: 'outline', size: 'large' }
      );
    }
  }, [onAuth]);

  return <div id="google-btn"></div>;
}

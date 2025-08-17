# Helper functions (JWT, DB, etc)
import os
import logging
import time
from google.oauth2 import id_token
from google.auth.transport import requests
from dotenv import load_dotenv
from google.auth import exceptions as ga_exceptions

# Load variables from .env if present (dev convenience)
load_dotenv()

def verify_google_token(id_token_str):
    """Verify a Google ID token and return its user info dict on success.

    Requires GOOGLE_CLIENT_ID to be set in the environment for strict audience
    checking. If missing, falls back to verification without audience (less
    strict) and logs a warning to aid local development.
    """
    audience = os.getenv('GOOGLE_CLIENT_ID')
    try:
        request = requests.Request()
        if audience:
            info = id_token.verify_oauth2_token(
                id_token_str, request, audience, clock_skew_in_seconds=10
            )
        else:
            logging.warning("GOOGLE_CLIENT_ID not set; verifying Google token without audience. Set GOOGLE_CLIENT_ID for strict checks.")
            info = id_token.verify_oauth2_token(
                id_token_str, request, clock_skew_in_seconds=10
            )
        return info  # contains 'email', 'email_verified', 'sub', 'name', etc.
    except ga_exceptions.InvalidValue as e:
        # Handle minor clock skew: "Token used too early"
        msg = str(e)
        if "Token used too early" in msg:
            logging.error("Google token used too early; retrying once after 2s.")
            time.sleep(2)
            try:
                request = requests.Request()
                if audience:
                    return id_token.verify_oauth2_token(
                        id_token_str, request, audience, clock_skew_in_seconds=10
                    )
                else:
                    return id_token.verify_oauth2_token(
                        id_token_str, request, clock_skew_in_seconds=10
                    )
            except Exception as e2:
                logging.exception("Retry verify failed: %s", e2)
                return None
        logging.exception("Google token verification failed: %s", e)
        return None
    except Exception as e:
        logging.exception("Google token verification failed: %s", e)
        return None

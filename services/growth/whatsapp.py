"""NIYAM WhatsApp Notification Service
Dual-mode notification system:
1. Live Twilio / Meta WhatsApp API: Dispatches real-time WhatsApp exception messages
   with interactive 1-tap mobile authorization links.
2. High-fidelity Sandbox Simulator: Logs alerts to event streams and drives the interactive
   smartphone UI frame when live credentials are not set.
"""
import os
import time
import hmac
import hashlib
import logging
from typing import Optional, Dict, Any
import httpx
from services.growth.engine import PolicyWaiver

logger = logging.getLogger("niyam.whatsapp")

SECRET_SALT = os.getenv("NIYAM_SIGNING_SALT", "niyam_production_salt_87364219")


class WhatsAppNotifier:
    """Dispatches human-in-the-loop WhatsApp authorization requests."""

    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_whatsapp: Optional[str] = None,
        default_phone: Optional[str] = None,
        public_base_url: Optional[str] = None,
        content_sid: Optional[str] = None
    ):
        self.account_sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = auth_token or os.getenv("TWILIO_AUTH_TOKEN")
        self.from_whatsapp = from_whatsapp or os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
        self.default_phone = default_phone or os.getenv("DEFAULT_PRINCIPAL_PHONE", "+919876543210")
        self.public_base_url = (public_base_url or os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")).rstrip("/")
        self.content_sid = content_sid or os.getenv("TWILIO_CONTENT_SID", "HXb131895de71a093156d1062e878de57c")

    def is_live_configured(self) -> bool:
        return bool(self.account_sid and self.auth_token and self.from_whatsapp)

    def generate_waiver_token(self, waiver_id: str, expires_at: float) -> str:
        """Generates a cryptographic single-use HMAC token for mobile approval links."""
        payload = f"{waiver_id}:{int(expires_at)}".encode()
        return hmac.new(SECRET_SALT.encode(), payload, hashlib.sha256).hexdigest()[:24]

    def verify_waiver_token(self, waiver_id: str, expires_at: float, token: str) -> bool:
        """Verifies if the submitted token matches the waiver parameters."""
        expected = self.generate_waiver_token(waiver_id, expires_at)
        return hmac.compare_digest(expected, token)

    def dispatch_waiver_alert(
        self,
        waiver: PolicyWaiver,
        item_title: str,
        recipient_phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """Dispatches an interactive WhatsApp authorization alert with a 1-tap mobile link."""
        phone = recipient_phone or self.default_phone
        token = self.generate_waiver_token(waiver.waiver_id, waiver.expires_at)
        approve_url = f"{self.public_base_url}/waivers/{waiver.waiver_id}/approve?token={token}"

        # Clean WhatsApp message formatting
        message_body = (
            f"🚨 *NIYAM Financial Authorization Request*\n\n"
            f"Autonomous buyer *{waiver.agent_id}* requested a purchase:\n"
            f"📦 *Item:* {item_title}\n"
            f"💰 *Cart Total:* ₹{waiver.cart_total:,.2f}\n"
            f"🛡️ *Policy Cap:* ₹{waiver.policy_limit:,.2f}\n"
            f"⚠️ *Exceeded By:* ₹{waiver.delta_amount:,.2f}\n\n"
            f"Do you authorize this one-time exception?\n\n"
            f"👉 *Tap to Authorize (Mobile Link):*\n"
            f"{approve_url}\n\n"
            f"⏱️ _Link expires in 15 minutes. Deterministic code enforces all other rules._"
        )

        result = {
            "waiver_id": waiver.waiver_id,
            "recipient_phone": phone,
            "approve_url": approve_url,
            "token": token,
            "message_preview": message_body,
            "mode": "simulated",
            "dispatched": True,
            "timestamp": time.time()
        }

        # If real Twilio credentials are configured, execute live HTTP dispatch
        if self.is_live_configured():
            try:
                twilio_res = self._send_twilio_whatsapp(phone, message_body)
                result["mode"] = "live_twilio"
                result["twilio_sid"] = twilio_res.get("sid")
                logger.info(f"[WhatsAppNotifier] Live alert sent via Twilio to {phone} (SID: {twilio_res.get('sid')})")
            except Exception as e:
                logger.warning(f"[WhatsAppNotifier] Twilio dispatch failed ({str(e)}). Falling back gracefully to simulated alert.")
                result["mode"] = "simulated_fallback"
                result["fallback_reason"] = str(e)
        else:
            logger.info(f"[WhatsAppNotifier] Sandbox mode: Simulated WhatsApp alert prepared for {phone}")

        return result

    def _send_twilio_whatsapp(self, to_phone: str, body: str) -> Dict[str, Any]:
        """Sends WhatsApp message via Twilio REST API with template support."""
        formatted_to = to_phone if to_phone.startswith("whatsapp:") else f"whatsapp:{to_phone}"
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        
        with httpx.Client(timeout=6.0) as client:
            # 1. Try template ContentSid first (required by Twilio free trial sandbox)
            if self.content_sid:
                template_data = {
                    "From": self.from_whatsapp,
                    "To": formatted_to,
                    "ContentSid": self.content_sid
                }
                resp = client.post(url, data=template_data, auth=(self.account_sid, self.auth_token))
                if resp.status_code < 400:
                    return resp.json()
            
            # 2. Fallback to freeform Body message
            data = {
                "From": self.from_whatsapp,
                "To": formatted_to,
                "Body": body
            }
            resp = client.post(url, data=data, auth=(self.account_sid, self.auth_token))
            if resp.status_code >= 400:
                raise RuntimeError(f"Twilio API Error {resp.status_code}: {resp.text}")
            return resp.json()

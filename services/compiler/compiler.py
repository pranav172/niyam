"""NIYAM Policy Compiler
Translates natural language (English / Hindi / Hinglish) into validated, immutable JSON SpendingPolicy objects.
Dual-mode compiler:
1. Production LLM Compiler: Calls Google Gemini, OpenAI, Groq, or Sarvam structured JSON APIs.
2. Built-in Deterministic Compiler: Instant local regex and semantic rule parser for offline & zero-latency demo reliability.
Includes prompt injection sanitization and automatic graceful fallback.
"""
import re
import os
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import httpx
from services.compiler.schema import SpendingPolicy, Limits, Constraints, TimeWindow, ReasonCode

logger = logging.getLogger("niyam.compiler")

# Known prompt injection / adversarial patterns to detect & neutralize
INJECTION_PATTERNS = [
    r"ignore (?:all )?(?:previous|prior) (?:instructions|rules|constraints)",
    r"disregard (?:all )?(?:limits|caps|restrictions)",
    r"override (?:all )?(?:safety|security|budget|policy)",
    r"you are now in (?:developer|dan|jailbreak|admin) mode",
    r"system override",
    r"unlimited (?:money|budget|funds|spend)",
    r"set (?:limit|budget|cap) to (?:infinity|infinite|999999999)",
    r"bypass (?:circuit breaker|policy|gateway|audit)"
]


class PolicyCompiler:
    """Compiles natural language into validated, versioned SpendingPolicy objects."""

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        groq_api_key: Optional[str] = None,
        sarvam_api_key: Optional[str] = None,
    ):
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.sarvam_api_key = sarvam_api_key or os.getenv("SARVAM_API_KEY")

    def compile(self, prompt: str, user_id: str, current_version: str = "v0") -> SpendingPolicy:
        """Compile a prompt into a verified SpendingPolicy with an incremented version."""
        # 1. Prompt Injection & Adversarial Sanitization
        sanitized_prompt, has_injection = self._sanitize_prompt(prompt)
        if has_injection:
            logger.warning(f"[SecurityAlert] Potential prompt injection detected in user prompt: {prompt[:80]}")

        # Calculate next version
        match = re.search(r"v(\d+)", current_version)
        next_ver_num = int(match.group(1)) + 1 if match else 1
        new_version = f"v{next_ver_num}"

        # 2. Attempt Real External LLM Compilation if configured
        policy_dict = None
        if self._has_llm_credentials():
            try:
                policy_dict = self._call_external_llm(sanitized_prompt, user_id, new_version)
            except Exception as e:
                logger.warning(f"[PolicyCompiler] External LLM call failed ({str(e)}). Gracefully falling back to deterministic local rule engine.")
                policy_dict = None

        # 3. Graceful Fallback: Local Semantic & Deterministic Parser
        if not policy_dict:
            policy_dict = self._parse_locally(sanitized_prompt, user_id, new_version)

        # 4. Strict Safety Clamping (Prevents rogue or malicious limits even if LLM hallucinates)
        policy_dict = self._apply_safety_clamps(policy_dict)

        # 5. Hard-fail schema validation via Pydantic
        try:
            policy = SpendingPolicy(**policy_dict)
            policy.raw_prompt = prompt
            return policy
        except Exception as e:
            raise ValueError(f"Schema validation failed for compiled policy: {str(e)}")

    def _has_llm_credentials(self) -> bool:
        return bool(self.gemini_api_key or self.openai_api_key or self.groq_api_key or self.sarvam_api_key)

    def _sanitize_prompt(self, prompt: str) -> tuple[str, bool]:
        """Detects adversarial injection attacks and cleans prompt."""
        lower = prompt.lower()
        has_injection = False
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, lower, re.IGNORECASE):
                has_injection = True
                prompt = re.sub(pattern, "[BLOCKED_ADVERSARIAL_OVERRIDE]", prompt, flags=re.IGNORECASE)
        return prompt, has_injection

    def _apply_safety_clamps(self, policy_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Enforces absolute non-bypassable safety ceilings across all policies."""
        limits = policy_dict.get("limits", {})
        # Absolute ceiling: ₹50,000 per tx without formal enterprise waiver
        max_allowed_tx = 50000.0
        if limits.get("max_per_transaction", 0) > max_allowed_tx:
            limits["max_per_transaction"] = max_allowed_tx

        # Monthly cap must be at least equal to per-tx limit
        if limits.get("monthly_cap", 0) < limits.get("max_per_transaction", 0):
            limits["monthly_cap"] = limits["max_per_transaction"] * 5

        policy_dict["limits"] = limits
        return policy_dict

    def _call_external_llm(self, prompt: str, user_id: str, version: str) -> Optional[Dict[str, Any]]:
        """Orchestrates structured LLM API calls with graceful fallback."""
        if self.gemini_api_key:
            return self._call_gemini(prompt, user_id, version)
        elif self.groq_api_key:
            return self._call_openai_compatible(
                api_key=self.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
                model="llama-3.3-70b-versatile",
                prompt=prompt,
                user_id=user_id,
                version=version
            )
        elif self.openai_api_key:
            return self._call_openai_compatible(
                api_key=self.openai_api_key,
                base_url="https://api.openai.com/v1",
                model="gpt-4o-mini",
                prompt=prompt,
                user_id=user_id,
                version=version
            )
        return None

    def _call_gemini(self, prompt: str, user_id: str, version: str) -> Optional[Dict[str, Any]]:
        """Calls Google Gemini REST API using structured JSON output mode."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
        system_instruction = (
            "You are the NIYAM Policy Compiler. Translate natural language spending policies (English, Hindi, Hinglish) "
            "into valid JSON matching the exact schema. Return ONLY a pure JSON object without markdown formatting.\n"
            "Schema format:\n"
            "{\n"
            f'  "policy_version": "{version}",\n'
            f'  "user_id": "{user_id}",\n'
            '  "limits": {"max_per_transaction": float, "monthly_cap": float, "category_caps": {"category": float}},\n'
            '  "constraints": {"returnable_only": bool, "cod_allowed_above": null or float, "allowed_categories": [string], "blocked_merchants": []},\n'
            '  "time_window": {"active_hours": "HH:MM-HH:MM" or null, "timezone": "Asia/Kolkata", "allowed_days": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]}\n'
            "}"
        )

        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": f"System Directive:\n{system_instruction}\n\nUser Input Policy:\n{prompt}"}]}
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1
            }
        }

        with httpx.Client(timeout=4.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                text_content = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text_content)
        return None

    def _call_openai_compatible(
        self,
        api_key: str,
        base_url: str,
        model: str,
        prompt: str,
        user_id: str,
        version: str
    ) -> Optional[Dict[str, Any]]:
        """Calls OpenAI/Groq compatible chat completions endpoint in JSON mode."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        system_msg = (
            "You are the NIYAM Policy Compiler. Translate natural language spending policies into pure JSON adhering to:\n"
            f'{{"policy_version": "{version}", "user_id": "{user_id}", "limits": {{"max_per_transaction": float, "monthly_cap": float, "category_caps": {{}}}}, '
            f'"constraints": {{"returnable_only": bool, "cod_allowed_above": null, "allowed_categories": [], "blocked_merchants": []}}, '
            f'"time_window": {{"active_hours": "09:00-21:00", "timezone": "Asia/Kolkata", "allowed_days": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]}}}}'
        )
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }
        with httpx.Client(timeout=4.0) as client:
            resp = client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                return json.loads(content)
        return None

    def _parse_locally(self, prompt: str, user_id: str, version: str) -> Dict[str, Any]:
        """Deterministic semantic rule extraction for Hinglish and English prompts."""
        lower = prompt.lower()

        # Defaults
        max_per_tx = 2000.0
        monthly_cap = 10000.0
        category_caps: Dict[str, float] = {}
        returnable_only = False
        cod_threshold = None
        active_hours = None
        allowed_categories = []

        # 1. Parse per-transaction limits
        tx_matches = re.findall(
            r"(?:max|maximum|limit|cap|upto|up to|per order|per transaction|ek baar me)\s*(?:₹|rs\.?|inr)?\s*(\d+(?:,\d+)*(?:\.\d+)?)",
            lower
        )
        if tx_matches:
            max_per_tx = float(tx_matches[0].replace(",", ""))
        else:
            num_per_order = re.findall(r"(\d+(?:,\d+)*)\s*(?:rs|rupees|inr)?\s*(?:per order|har order)", lower)
            if num_per_order:
                max_per_tx = float(num_per_order[0].replace(",", ""))

        # 2. Parse monthly limits
        monthly_matches = re.findall(
            r"(?:monthly|per month|month|mahine ka|mahine me)\s*(?:budget|cap|limit|spend|kharcha)?\s*(?:₹|rs\.?|inr)?\s*(\d+(?:,\d+)*(?:\.\d+)?)",
            lower
        )
        if monthly_matches:
            monthly_cap = float(monthly_matches[0].replace(",", ""))
        else:
            rev_monthly = re.findall(r"(\d+(?:,\d+)*)\s*(?:rs|rupees|inr)?\s*(?:monthly|har mahine)", lower)
            if rev_monthly:
                monthly_cap = float(rev_monthly[0].replace(",", ""))

        # Ensure monthly_cap >= max_per_tx
        if monthly_cap < max_per_tx:
            monthly_cap = max_per_tx * 5

        # 3. Category caps & prohibitions
        if any(w in lower for w in ["no electronics", "electronics bilkul nahi", "electronics mat", "electronics ban"]):
            category_caps["electronics"] = 0.0

        toy_match = re.findall(r"(?:toys?|khilone)\s*(?:ke liye)?\s*(?:max|limit)?\s*(?:₹|rs\.?)?\s*(\d+)", lower)
        if toy_match:
            category_caps["toys"] = float(toy_match[0])
        elif "toy" in lower or "toys" in lower or "khilone" in lower:
            category_caps["toys"] = max_per_tx

        groc_match = re.findall(r"(?:groceries|grocery|ration)\s*(?:ke liye)?\s*(?:max|limit)?\s*(?:₹|rs\.?)?\s*(\d+)", lower)
        if groc_match:
            category_caps["groceries"] = float(groc_match[0])

        # 4. Constraints
        if any(w in lower for w in ["returnable only", "sirf returnable", "returnable", "wapas hona chahiye"]):
            returnable_only = True

        cod_above = re.findall(r"cod\s*(?:allowed|above|upar)?\s*(?:₹|rs\.?)?\s*(\d+)", lower)
        if cod_above and "above" in lower:
            cod_threshold = float(cod_above[0])

        # 5. Time window
        time_match = re.search(r"(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})", lower)
        if time_match:
            active_hours = f"{time_match.group(1)}-{time_match.group(2)}"
        elif any(w in lower for w in ["raat 9 baje", "9 pm", "21:00", "after 9pm"]):
            active_hours = "09:00-21:00"

        # Allowed categories list
        if "toys" in category_caps:
            allowed_categories.append("toys")
        if "groceries" in category_caps:
            allowed_categories.append("groceries")
        if "books" in lower:
            allowed_categories.append("books")

        result: Dict[str, Any] = {
            "policy_version": version,
            "user_id": user_id,
            "limits": {
                "max_per_transaction": max_per_tx,
                "monthly_cap": monthly_cap,
                "category_caps": category_caps
            },
            "constraints": {
                "returnable_only": returnable_only,
                "cod_allowed_above": cod_threshold,
                "allowed_categories": allowed_categories,
                "blocked_merchants": []
            }
        }

        if active_hours:
            result["time_window"] = {
                "active_hours": active_hours,
                "timezone": "Asia/Kolkata",
                "allowed_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            }

        return result

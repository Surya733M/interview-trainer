"""
services/granite_service.py — IBM Granite LLM Integration
===========================================================
Wraps the IBM watsonx.ai Python SDK to call IBM Granite models.

Primary model  : ibm/granite-13b-chat-v2
Fallback       : Returns structured mock data if credentials missing

All generation calls are structured to return valid JSON so the
application can parse the output reliably.
"""

import json
import re
from typing import Optional

from app.config import settings
from app.utils.logger import logger


class GraniteService:
    """IBM Granite text generation service with lazy initialisation."""

    def __init__(self):
        self._model = None
        self._available = None  # None = not yet checked

    def _load(self) -> bool:
        """Initialise the Granite model. Returns True if successful."""
        if self._available is not None:
            return self._available

        if (not settings.watsonx_api_key or
                settings.watsonx_api_key == "your-ibm-cloud-api-key-here"):
            logger.warning(
                "IBM Granite: WATSONX_API_KEY not set. "
                "Using mock responses. Set credentials in .env to enable real AI."
            )
            self._available = False
            return False

        try:
            from ibm_watsonx_ai import Credentials
            from ibm_watsonx_ai.foundation_models import ModelInference
            from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

            creds = Credentials(
                url=settings.watsonx_url,
                api_key=settings.watsonx_api_key,
            )
            self._model = ModelInference(
                model_id=settings.granite_model_id,
                credentials=creds,
                project_id=settings.watsonx_project_id,
                params={
                    GenParams.MAX_NEW_TOKENS:  2048,
                    GenParams.TEMPERATURE:     0.7,
                    GenParams.TOP_P:           0.9,
                    GenParams.REPETITION_PENALTY: 1.1,
                },
            )
            self._available = True
            logger.info(f"IBM Granite loaded: {settings.granite_model_id}")
            return True

        except Exception as e:
            logger.error(f"IBM Granite init failed: {e}. Using mock responses.")
            self._available = False
            return False

    def generate(self, prompt: str, max_tokens: int = 2048) -> str:
        """
        Generate text from a prompt.

        Returns:
            Generated text string. Falls back to empty string on error.
        """
        if not self._load():
            return ""

        try:
            result = self._model.generate_text(prompt=prompt)
            return result if isinstance(result, str) else str(result)
        except Exception as e:
            logger.error(f"Granite generation failed: {e}")
            return ""

    def generate_json(self, prompt: str) -> dict | list:
        """
        Generate text and parse as JSON.
        Handles Granite's tendency to include extra text around JSON.
        Returns empty dict/list on failure.
        """
        raw = self.generate(prompt)
        return _extract_json(raw)

    @property
    def is_available(self) -> bool:
        return self._load()


def _extract_json(text: str) -> dict | list:
    """
    Extract JSON from Granite output which may include surrounding text.
    Tries multiple strategies to find valid JSON.
    """
    if not text:
        return {}

    # Strategy 1: direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Strategy 2: find JSON array or object using regex
    patterns = [
        r'\[[\s\S]*\]',   # JSON array
        r'\{[\s\S]*\}',   # JSON object
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                continue

    # Strategy 3: find content between ```json ``` markers
    code_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if code_match:
        try:
            return json.loads(code_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    logger.warning(f"Could not extract JSON from Granite output: {text[:200]}")
    return {}


# Module-level singleton
granite = GraniteService()

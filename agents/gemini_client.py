import json
import logging
from typing import Any, Dict, List

import numpy as np

from config.settings import config

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Wrapper around Google Gemini text generation + embeddings.
    Falls back to deterministic local behavior if Gemini is unavailable.
    """

    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        self.model_name = config.GEMINI_MODEL
        self.embedding_model = config.GEMINI_EMBEDDING_MODEL
        self.enabled = False
        self._genai = None
        self._resolved_embedding_model: str | None = None
        self._embedding_disabled = False

        if not self.api_key:
            logger.info("Gemini API key not configured, using local fallbacks.")
            return

        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            self._genai = genai
            self.enabled = True
        except Exception as exc:
            logger.warning(f"Gemini initialization failed, fallback enabled: {exc}")

    def generate_text(self, prompt: str, system_instruction: str | None = None) -> str:
        if not self.enabled or self._genai is None:
            return ""

        try:
            generation_config: Dict[str, Any] = {
                "temperature": config.TEMPERATURE,
                "max_output_tokens": config.MAX_TOKENS,
            }
            model = self._genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction,
                generation_config=generation_config,
            )
            result = model.generate_content(prompt)
            text = getattr(result, "text", None)
            return text.strip() if text else ""
        except Exception as exc:
            logger.warning(f"Gemini text generation failed: {exc}")
            return ""

    def generate_json(self, prompt: str, fallback: Dict[str, Any], system_instruction: str | None = None) -> Dict[str, Any]:
        raw = self.generate_text(
            prompt=prompt,
            system_instruction=system_instruction
            or "Respond with strictly valid JSON only. No markdown fences.",
        )
        if not raw:
            return fallback

        candidate = raw.strip()
        if "```" in candidate:
            candidate = candidate.replace("```json", "").replace("```", "").strip()
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
            return fallback
        except Exception:
            return fallback

    def _embedding_model_candidates(self) -> List[str]:
        candidates: List[str] = []
        configured = (self.embedding_model or "").strip()
        if configured:
            candidates.append(configured)
            if configured.startswith("models/"):
                candidates.append(configured.split("/", 1)[1])
            else:
                candidates.append(f"models/{configured}")

        # Common Gemini embedding model aliases across client versions.
        candidates.extend(["models/embedding-001", "embedding-001"])

        deduped: List[str] = []
        seen = set()
        for item in candidates:
            if item and item not in seen:
                deduped.append(item)
                seen.add(item)
        return deduped

    def embed_text(self, text: str, dimensions: int = 384) -> List[float]:
        if self.enabled and self._genai is not None and not self._embedding_disabled:
            model_candidates = self._embedding_model_candidates()
            if self._resolved_embedding_model:
                model_candidates = [self._resolved_embedding_model] + [
                    m for m in model_candidates if m != self._resolved_embedding_model
                ]

            last_error = None
            for model_name in model_candidates:
                try:
                    response = self._genai.embed_content(
                        model=model_name,
                        content=text,
                        task_type="retrieval_document",
                    )
                    values = []
                    if isinstance(response, dict):
                        values = response.get("embedding", [])
                    else:
                        values = getattr(response, "embedding", []) or []

                    if values:
                        self._resolved_embedding_model = model_name
                        return values
                except Exception as exc:
                    last_error = exc

            if last_error is not None:
                # Disable remote embedding attempts for this process after repeated model failures.
                self._embedding_disabled = True
                logger.warning(
                    f"Gemini embedding unavailable; switching to local fallback for this run: {last_error}"
                )

        return self._deterministic_local_embedding(text, dimensions=dimensions)

    @staticmethod
    def _deterministic_local_embedding(text: str, dimensions: int = 384) -> List[float]:
        # Deterministic hash-based fallback; not semantic but keeps pipeline functional.
        values = np.zeros(dimensions, dtype=np.float32)
        tokens = [token for token in text.lower().split() if token]
        if not tokens:
            return values.tolist()
        for token in tokens:
            idx = abs(hash(token)) % dimensions
            values[idx] += 1.0
        norm = np.linalg.norm(values)
        if norm > 0:
            values = values / norm
        return values.tolist()

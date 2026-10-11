import json
import logging

import google.generativeai as genai
import groq

from app.core.config import settings

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are looking at an image of a job vacancy posting \
(poster, screenshot, or flyer). Extract the following fields as JSON and \
nothing else — no markdown fences, no commentary:

{
  "job_title": string or null,
  "company": string or null,
  "description": string or null,
  "skills_required": array of strings or null,
  "location": string or null,
  "employment_type": string or null,
  "salary_range": string or null
}

Rules:
- If a field is not visible or you are not confident, use null. Do not guess or invent values.
- "skills_required" should be short, individual skill/technology names, not full sentences.
- Respond with raw JSON only.
"""

_EXPECTED_FIELDS = [
    "job_title",
    "company",
    "description",
    "skills_required",
    "location",
    "employment_type",
    "salary_range",
]


class VisionLLMError(Exception):
    """Raised when a provider call fails or returns unparseable output."""


def _parse_json_response(text: str, provider: str) -> dict:
    # Models sometimes add a stray sentence or markdown fence around the
    # JSON even when told not to — pull out the outermost {...} rather than
    # requiring the whole response to be valid JSON on its own.
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        logger.error("%s returned no JSON object. Raw response: %r", provider, text[:500])
        raise VisionLLMError(f"{provider} did not return a JSON object")

    candidate = text[start : end + 1]
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        logger.error("%s returned malformed JSON. Raw response: %r", provider, text[:500])
        raise VisionLLMError(f"{provider} returned malformed JSON: {exc}") from exc

    return {field: data.get(field) for field in _EXPECTED_FIELDS}


def _call_gemini(image_bytes: bytes, media_type: str) -> dict:
    if not settings.gemini_api_key:
        raise VisionLLMError("GEMINI_API_KEY is not set")

    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_vision_model)
        response = model.generate_content(
            [
                EXTRACTION_PROMPT,
                {"mime_type": media_type, "data": image_bytes},
            ]
        )
    except Exception as exc:  # google-generativeai raises various exception types
        raise VisionLLMError(f"Gemini API error: {exc}") from exc

    text = response.text or ""
    return _parse_json_response(text, "gemini")


def _call_groq(image_bytes: bytes, media_type: str) -> dict:
    import base64

    if not settings.groq_api_key:
        raise VisionLLMError("GROQ_API_KEY is not set")

    client = groq.Groq(api_key=settings.groq_api_key)
    b64_image = base64.standard_b64encode(image_bytes).decode("utf-8")

    try:
        response = client.chat.completions.create(
            model=settings.groq_vision_model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": EXTRACTION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{media_type};base64,{b64_image}"},
                        },
                    ],
                }
            ],
        )
    except groq.APIError as exc:
        raise VisionLLMError(f"Groq API error: {exc}") from exc

    text = response.choices[0].message.content or ""
    return _parse_json_response(text, "groq")


def extract_job_data(image_bytes: bytes, media_type: str) -> tuple[dict, str, dict]:
    """
    Tries Gemini first (free tier); on any failure (missing key, API error,
    timeout, malformed JSON output) falls back to Groq (also free tier) once.
    If both fail, the Groq exception propagates (with the Gemini failure
    already logged below), so the caller sees a real cause instead of a
    silent 502.

    Returns (extracted_fields, provider_name, raw_response_for_audit).
    """
    try:
        fields = _call_gemini(image_bytes, media_type)
        return fields, "gemini", fields
    except Exception as exc:
        logger.warning("Gemini extraction failed, falling back to Groq: %s", exc)

    fields = _call_groq(image_bytes, media_type)
    return fields, "groq", fields

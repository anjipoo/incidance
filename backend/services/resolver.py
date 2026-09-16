import os
import json
from google import genai
from backend.services.retriever import search_similar
from backend.services.classifier import classify

# Change this in one place if the model name changes or you want to try another.
# gemini-2.5-flash is a good free-tier-friendly choice: fast and cheap enough
# for a portfolio project with frequent requests during testing.
MODEL_NAME = "gemini-2.5-flash"

_client: genai.Client | None = None


def get_client() -> genai.Client:
    # Lazy singleton, same pattern as the SentenceTransformer model.
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def build_rag_context(similar_incidents: list[dict]) -> str:
    # Formats retrieved incidents as readable context for the prompt.
    # This IS the "retrieval-augmented" part of RAG: we hand the model
    # concrete prior cases instead of asking it to reason from nothing.
    if not similar_incidents:
        return "No similar historical incidents were found."

    sections = []
    for i, incident in enumerate(similar_incidents, start=1):
        resolution_lines = "\n".join(f"- {step}" for step in incident["resolution"])
        sections.append(
            f"{i}.\n"
            f"Log: {incident['log']}\n"
            f"Category: {incident['category']}\n"
            f"Root cause: {incident['root_cause']}\n"
            f"Resolution:\n{resolution_lines}"
        )
    return "\n\n".join(sections)


def build_prompt(cleaned_log: str, rule_based_category: str, rag_context: str) -> str:
    # The prompt is deliberately explicit about not inventing facts and
    # not overclaiming certainty — this matters for a project that's
    # meant to demonstrate responsible AI system design, not just a demo.
    return f"""You are an incident analysis assistant for a software engineering team.

Analyze the current incident below using the retrieved historical incidents as
supporting context. The historical incidents are retrieved evidence, not
guaranteed truth — they may be similar but not identical to the current case.

Current incident log:
{cleaned_log}

A simple keyword-based classifier suggested this category: {rule_based_category}
(This is a rough first guess — confirm, refine, or override it based on the
actual log content.)

Similar historical incidents:
{rag_context}

Instructions:
- Do not invent facts that are not supported by the log or the historical context.
- Clearly distinguish a likely root cause from a confirmed root cause. If the
  log does not definitively establish the cause, say it is a hypothesis, not
  a confirmed fact.
- Base recommended actions on the incident and the retrieved context.
- If there is insufficient information to be confident, say so honestly
  rather than guessing with false certainty.
- Return ONLY a JSON object in exactly this shape, with no other text,
  no markdown code fences, and no explanation outside the JSON:

{{
  "category": "one of: database, network, authentication, filesystem, memory, api, dns, permission, configuration, application, unknown",
  "severity": "one of: low, medium, high, critical",
  "root_cause": "a concise root cause hypothesis, phrased as likely/probable if not certain",
  "recommended_actions": ["action 1", "action 2", "action 3"],
  "confidence": 0.0 to 1.0
}}"""


def call_gemini(prompt: str) -> dict:
    # Sends the prompt to Gemini and parses the structured JSON response.
    client = get_client()

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )
    except Exception as e:
        raise RuntimeError(f"Gemini API call failed: {e}") from e

    raw_text = response.text.strip()

    # Gemini sometimes wraps JSON in markdown fences despite instructions
    # not to — strip them defensively rather than relying on the prompt alone.
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Gemini returned malformed JSON: {raw_text[:200]}") from e


def compute_confidence(gemini_confidence: float, top_similarity: float, category_agrees: bool) -> float:
    # Combines three simple signals into one estimated confidence score.
    # This is intentionally simple and NOT a scientifically calibrated
    # probability — it's a weighted blend meant to be explainable, not exact.
    agreement_bonus = 0.05 if category_agrees else -0.05
    blended = (0.5 * gemini_confidence) + (0.4 * top_similarity) + agreement_bonus
    return round(max(0.0, min(1.0, blended)), 2)


def analyze_incident(cleaned_log: str) -> dict:
    # Full RAG pipeline: classify -> retrieve -> build context -> call Gemini
    # -> blend confidence. This is the single entry point main.py will call.
    rule_based_category = classify(cleaned_log)
    similar_incidents = search_similar(cleaned_log, top_k=3)
    rag_context = build_rag_context(similar_incidents)

    prompt = build_prompt(cleaned_log, rule_based_category, rag_context)
    result = call_gemini(prompt)

    top_similarity = similar_incidents[0]["similarity"] if similar_incidents else 0.0
    category_agrees = result.get("category") == rule_based_category

    result["confidence"] = compute_confidence(
        gemini_confidence=float(result.get("confidence", 0.5)),
        top_similarity=top_similarity,
        category_agrees=category_agrees,
    )
    result["similar_incidents"] = similar_incidents

    return result
import re


def clean_log(raw_log: str) -> str:
    # Preprocesses a raw incident log before classification/embedding.
    # Kept deliberately simple: normalize noisy variable data (timestamps, IPs)
    # so that semantically similar logs embed closer together, while preserving
    # the actual error text that carries meaning.

    if not raw_log or not raw_log.strip():
        raise ValueError("Log input cannot be empty")

    text = raw_log.strip()

    # Collapse multiple whitespace/newlines into single spaces.
    text = re.sub(r"\s+", " ", text)

    # Normalize timestamps like "2026-09-16 14:32:10" -> "<TIMESTAMP>".
    text = re.sub(
        r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}",
        "<TIMESTAMP>",
        text,
    )

    # Normalize IPv4 addresses -> "<IP>", optionally with a port.
    text = re.sub(
        r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?\b",
        "<IP>",
        text,
    )

    return text.strip()


def extract_error_indicators(cleaned_log: str) -> list[str]:
    # Pulls out common error-signal keywords, useful mainly for debugging/logging
    # what the parser "saw" — not used for classification itself (that's Step 5).
    indicators = [
        "error", "failed", "failure", "exception", "timeout", "timed out",
        "refused", "denied", "unavailable", "unreachable", "crash",
    ]
    lower = cleaned_log.lower()
    return [word for word in indicators if word in lower]
# Simple rule-based classifier. Each category maps to a list of keyword
# phrases; the first category with a matching phrase wins. This is
# intentionally not ML-based — it's a fast, explainable baseline that
# runs before the semantic (embedding + FAISS) layer takes over.

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "database": [
        "postgres", "postgresql", "mysql", "sqlite", "database",
        "connection pool", "deadlock", "replica", "migration failed",
        "query timed out", "db connection",
    ],
    "network": [
        "connection refused", "connection timeout", "socket timeout",
        "unreachable host", "network interface", "packet loss",
        "connection reset", "tls handshake", "no route to",
    ],
    "api": [
        "http 500", "http 502", "http 503", "http 429",
        "bad gateway", "service unavailable", "malformed api response",
        "webhook", "graphql", "api timeout",
    ],
    "dns": [
        "dns", "name resolution", "unknown host", "getaddrinfo",
        "servfail", "host not found",
    ],
    "filesystem": [
        "no space left", "file not found", "filenotfounderror",
        "corrupted file", "i/o error", "mount point", "stale file handle",
        "disk full",
    ],
    "memory": [
        "out of memory", "outofmemoryerror", "heap space", "oomkilled",
        "gc overhead", "swap usage", "segmentation fault",
        "memory allocation failed",
    ],
    "authentication": [
        "authentication failed", "access token expired", "invalid credentials",
        "unauthorized", "jwt", "oauth", "session expired",
        "multi-factor", "auth-server",
    ],
    "permission": [
        "permission denied", "access denied", "insufficient privileges",
        "iam role", "sudoers", "rbac",
    ],
    "configuration": [
        "invalid configuration", "missing environment variable",
        "invalid port", "malformed configuration", "config reload failed",
        "duplicate configuration key", "feature flag",
    ],
    "application": [
        "unhandled exception", "importerror", "infinite loop",
        "job queue backlog", "cache invalidation", "scheduled job",
        "nonetype",
    ],
}


def classify(cleaned_log: str) -> str:
    # Returns the first matching category, or "unknown" if nothing matches.
    lower = cleaned_log.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lower:
                return category

    return "unknown"
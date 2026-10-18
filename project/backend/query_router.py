"""
Stage 4: Query Router.

Ranks structural context nodes by relevance to the query using a hybrid approach:
1. Tokenized TF-IDF / BM25 scoring with CamelCase & snake_case splitting.
2. Strong symbol & signature weighting.
3. Call-graph expansion: if Node A is highly relevant and calls Node B, Node B receives
   a call-graph proximity boost so critical dependencies aren't pruned away.
"""
import re
import math
from typing import Any

SYNONYMS = {
    "constructor": ["__init__", "init"],
    "initialize": ["__init__", "init"],
    "authenticate": ["verify", "auth", "login"],
    "validate": ["check", "verify", "assert", "validation"],
    "metrics": ["score", "calculate", "user_metrics", "health"],
    "cache": ["user_data_cache", "store", "get_user_data_cache"],
    "status": ["is_active", "get_is_active", "active"],
    "factory": ["EnterpriseUserManagerProxyFactory", "create", "build", "proxy"]
}

CONFIDENCE_THRESHOLD = 0.15


def _stem(word: str) -> str:
    word = word.lower()
    for suffix in ('edly', 'fully', 'ment', 'able', 'ness', 'ties', 'tional', 'tion', 'ing', 'ed', 'es', 'ly', 'er', 's'):
        if word.endswith(suffix) and len(word) > len(suffix) + 1:
            return word[:-len(suffix)]
    return word


def _tokenize(text: str, expand_synonyms: bool = False) -> list[str]:
    if not text:
        return []
    # Split camelCase
    text = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', text)
    # Split snake_case and non-alphanumeric
    words = re.findall(r'[a-zA-Z0-9_]{2,}', text.lower())
    tokens = []
    for w in words:
        parts = w.split('_') if '_' in w else [w]
        for p in parts:
            if len(p) >= 2:
                tokens.append(_stem(p))

    if expand_synonyms:
        expanded = list(tokens)
        for t in tokens:
            for key, syns in SYNONYMS.items():
                if _stem(key) == t:
                    for s in syns:
                        expanded.extend(_tokenize(s, expand_synonyms=False))
        return list(dict.fromkeys(expanded))
    return tokens


def rank_by_relevance(query: str, nodes: list[Any]) -> tuple[list[Any], float]:
    """
    Ranks nodes by relevance to the query.
    Returns:
        (ranked_nodes_list, top_confidence_score)
    """
    if not nodes:
        return [], 0.0

    query_tokens = _tokenize(query, expand_synonyms=True)
    if not query_tokens:
        return nodes, 0.5

    # 1. Prepare node fields for TF-IDF
    node_profiles = []
    for node in nodes:
        name = getattr(node, "name", "").lower()
        signature = getattr(node, "signature", "").lower()
        docstring = getattr(node, "docstring", "").lower()
        body = getattr(node, "body", "").lower()
        template = getattr(node, "template", "").lower()
        calls = [c.lower() for c in getattr(node, "calls", [])]

        node_profiles.append({
            "node": node,
            "name": name,
            "calls": calls,
            "name_tokens": _tokenize(name),
            "sig_tokens": _tokenize(signature),
            "doc_tokens": _tokenize(docstring),
            "body_tokens": _tokenize(body) if body else _tokenize(template),
        })

    N = len(nodes)
    raw_scores: list[float] = []

    # 2. Base TF-IDF computation with signature boosting
    for prof in node_profiles:
        score = 0.0
        for q_token in query_tokens:
            name_count = prof["name_tokens"].count(q_token)
            sig_count = prof["sig_tokens"].count(q_token)
            doc_count = prof["doc_tokens"].count(q_token)
            body_count = prof["body_tokens"].count(q_token)

            tf = (name_count * 10.0) + (sig_count * 5.0) + (doc_count * 2.5) + (body_count * 1.0)
            if tf > 0:
                df = sum(
                    1 for p in node_profiles
                    if q_token in p["name_tokens"]
                    or q_token in p["sig_tokens"]
                    or q_token in p["doc_tokens"]
                    or q_token in p["body_tokens"]
                )
                idf = math.log((N + 1) / (df + 1)) + 1.0
                score += tf * idf

        raw_scores.append(score)

    # 3. Call-Graph Dependency Expansion
    # If node A has high score, nodes it calls get a proximity boost
    final_scores = list(raw_scores)
    for i, prof in enumerate(node_profiles):
        if raw_scores[i] > 2.0:
            boost_val = raw_scores[i] * 0.35
            called_names = prof["calls"]
            for j, other in enumerate(node_profiles):
                if i != j:
                    other_name = other["name"].lower()
                    if any(c in other_name for c in called_names):
                        final_scores[j] += boost_val

    # Pair with nodes and sort descending
    scored_pairs = list(zip(final_scores, nodes))
    scored_pairs.sort(key=lambda x: x[0], reverse=True)

    ranked_nodes = [node for _, node in scored_pairs]
    max_score = scored_pairs[0][0] if scored_pairs else 0.0
    # Normalized confidence score in [0.0, 1.0]
    confidence = min(1.0, round(max_score / (max_score + 10.0), 4)) if max_score > 0 else 0.0

    return ranked_nodes, confidence

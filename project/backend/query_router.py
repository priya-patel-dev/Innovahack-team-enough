"""
Stage 4: Query Router.

Ranks structural nodes by relevance to the live query using a fast, lightweight
TF-IDF scoring algorithm with signature/name boosting and suffix-stripping stemming.
Runs completely in pure Python on CPU with sub-millisecond latency.
"""
import re
import math

def _stem(word: str) -> str:
    word = word.lower()
    # Strip common plural/tense/nominal suffixes to enable fuzzy matching
    for suffix in ('edly', 'fully', 'ment', 'able', 'ness', 'ties', 'tional', 'tion', 'ing', 'ed', 'es', 'ly', 'er', 's'):
        if word.endswith(suffix) and len(word) > len(suffix) + 1:
            return word[:-len(suffix)]
    return word

def _tokenize(text: str) -> list[str]:
    # Lowercase, extract alphanumeric words, and stem them
    words = re.findall(r'[a-zA-Z0-9]{2,}', text.lower())
    return [_stem(w) for w in words]

def rank_by_relevance(query: str, nodes: list) -> list:
    if not nodes:
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return nodes

    node_contents = []
    for node in nodes:
        name = getattr(node, "name", "").lower()
        signature = getattr(node, "signature", "").lower()
        docstring = getattr(node, "docstring", "").lower()
        body = getattr(node, "body", "").lower()
        template = getattr(node, "template", "").lower()
        
        node_contents.append({
            "node": node,
            "name_tokens": _tokenize(name),
            "sig_tokens": _tokenize(signature),
            "doc_tokens": _tokenize(docstring),
            "body_tokens": _tokenize(body) if body else _tokenize(template)
        })

    scores = []
    N = len(nodes)
    
    for content in node_contents:
        score = 0.0
        for q_token in query_tokens:
            # Term Frequency in different fields
            name_count = content["name_tokens"].count(q_token)
            sig_count = content["sig_tokens"].count(q_token)
            doc_count = content["doc_tokens"].count(q_token)
            body_count = content["body_tokens"].count(q_token)
            
            # Weighted TF (increased name boost to 8.0 and sig to 4.0)
            tf = (name_count * 8.0) + (sig_count * 4.0) + (doc_count * 2.0) + (body_count * 1.0)
            
            if tf > 0:
                # Document Frequency (DF) across the document corpus
                df = sum(
                    1 for c in node_contents 
                    if q_token in c["name_tokens"] 
                    or q_token in c["sig_tokens"] 
                    or q_token in c["doc_tokens"] 
                    or q_token in c["body_tokens"]
                )
                
                # Smoothed IDF
                idf = math.log((N + 1) / (df + 1)) + 1.0
                score += tf * idf
            
        scores.append((score, content["node"]))

    # Sort nodes by score descending, maintaining original order for ties
    ranked = [node for _, node in sorted(scores, key=lambda x: -x[0])]
    return ranked

"""
Stage 2 (logs): Structural Layer.

Clusters log lines into parameterized templates (using Drain3 when available,
or regex-based frequency clustering as a zero-dependency fallback).
Compresses repetitive log storms (e.g. 5,000 occurrences of connection failures)
into a single template summary with token metrics and sample occurrences.
"""
import hashlib
import re
from dataclasses import dataclass, field
from collections import defaultdict

try:
    from drain3 import TemplateMiner
    from drain3.template_miner_config import TemplateMinerConfig
    _DRAIN3_AVAILABLE = True
except ImportError:
    _DRAIN3_AVAILABLE = False


@dataclass
class LogNode:
    id: str
    name: str
    kind: str = "log_template"
    template: str = ""
    count: int = 0
    sample_lines: list[str] = field(default_factory=list)
    token_estimate: int = 0
    stub: str = ""

    def content_hash(self) -> str:
        return hashlib.sha256(self.template.encode("utf-8")).hexdigest()


# High-entropy parameter regexes for masking
IP_PATTERN = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')
UUID_PATTERN = re.compile(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b')
HEX_PATTERN = re.compile(r'\b0x[0-9a-fA-F]+\b')
TS_PATTERN = re.compile(
    r'\b(?:\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?'
    r'|\d{2}/\d{2}/\d{4}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?'
    r'|\d{2}:\d{2}:\d{2}(?:\.\d+)?)\b'
)
NUM_PATTERN = re.compile(r'\b\d+\b')


def preprocess_log_line(line: str) -> str:
    """Mask high-entropy components to extract recurring event templates."""
    line = TS_PATTERN.sub('<TS>', line)
    line = UUID_PATTERN.sub('<UUID>', line)
    line = IP_PATTERN.sub('<IP>', line)
    line = HEX_PATTERN.sub('<HEX>', line)
    return line


def _fallback_log_clustering(raw_logs: str, max_samples_per_cluster: int = 2) -> list[LogNode]:
    """Pure-Python heuristic template clustering fallback when drain3 is not installed."""
    clusters = defaultdict(list)
    template_map = {}

    for line in raw_logs.splitlines():
        line = line.strip()
        if not line:
            continue
        cleaned = preprocess_log_line(line)
        # Generalized template: replace numbers with <*>
        template = NUM_PATTERN.sub('<*>', cleaned)
        t_hash = hashlib.md5(template.encode("utf-8")).hexdigest()[:8]
        clusters[t_hash].append(line)
        template_map[t_hash] = template

    nodes: list[LogNode] = []
    for cid, (t_hash, lines) in enumerate(clusters.items()):
        template = template_map[t_hash]
        count = len(lines)
        stub = f"LOG TEMPLATE: {template} (occurred {count}x) [collapsed: node 'log_cluster_{cid}']"
        node = LogNode(
            id=f"log_cluster_{cid}",
            name=template[:80],
            template=template,
            count=count,
            sample_lines=lines[:max_samples_per_cluster],
            token_estimate=int(len(template.split()) + max_samples_per_cluster * 6),
            stub=stub
        )
        nodes.append(node)
    return nodes


def build_log_templates(raw_logs: str, max_samples_per_cluster: int = 2) -> list[LogNode]:
    """Clusters logs into structured nodes using Drain3 or heuristic fallback."""
    if not raw_logs or not raw_logs.strip():
        return []

    if not _DRAIN3_AVAILABLE:
        return _fallback_log_clustering(raw_logs, max_samples_per_cluster)

    try:
        config = TemplateMinerConfig()
        miner = TemplateMiner(config=config)
        clusters: dict[int, list[str]] = {}

        for line in raw_logs.splitlines():
            line = line.strip()
            if not line:
                continue
            cleaned = preprocess_log_line(line)
            res = miner.add_log_message(cleaned)
            cluster_id = res["cluster_id"]
            clusters.setdefault(cluster_id, []).append(line)

        nodes: list[LogNode] = []
        for cluster in miner.drain.clusters:
            lines = clusters.get(cluster.cluster_id, [])
            template = cluster.get_template()
            stub = f"LOG TEMPLATE: {template} (occurred {len(lines)}x) [collapsed: node 'log_cluster_{cluster.cluster_id}']"
            node = LogNode(
                id=f"log_cluster_{cluster.cluster_id}",
                name=template[:80],
                template=template,
                count=len(lines),
                sample_lines=lines[:max_samples_per_cluster],
                token_estimate=int(len(template.split()) + max_samples_per_cluster * 6),
                stub=stub
            )
            nodes.append(node)
        return nodes
    except Exception:
        return _fallback_log_clustering(raw_logs, max_samples_per_cluster)

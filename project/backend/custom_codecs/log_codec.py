"""
Stage 2 (logs): Structural Layer.

Uses Drain3 to cluster log lines into templates, e.g.
  "User <ID> failed login at <TS>"  x 47 occurrences
Collapses repeats into {pattern, count, sample_lines} instead of keeping
every raw line - this alone is usually 30-40% of your compression win,
before any AI-based pruning happens.
"""
import hashlib
import re
from dataclasses import dataclass, field

from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig


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
        return hashlib.sha256(self.template.encode()).hexdigest()


# High-entropy parameter regexes for masking
IP_PATTERN = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')
UUID_PATTERN = re.compile(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b')
HEX_PATTERN = re.compile(r'\b0x[0-9a-fA-F]+\b')
TS_PATTERN = re.compile(
    r'\b(?:\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?'  # ISO
    r'|\d{2}/\d{2}/\d{4}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?'        # US
    r'|\d{2}:\d{2}:\d{2}(?:\.\d+)?)\b'                          # Time
)


def preprocess_log_line(line: str) -> str:
    """Mask high-entropy parts to improve clustering and token size."""
    line = TS_PATTERN.sub('<TS>', line)
    line = UUID_PATTERN.sub('<UUID>', line)
    line = IP_PATTERN.sub('<IP>', line)
    line = HEX_PATTERN.sub('<HEX>', line)
    return line


def build_log_templates(raw_logs: str, max_samples_per_cluster: int = 2) -> list[LogNode]:
    config = TemplateMinerConfig()
    # use library defaults; tune drain3.ini for real data
    miner = TemplateMiner(config=config)

    clusters: dict[int, list[str]] = {}

    for line in raw_logs.splitlines():
        line = line.strip()
        if not line:
            continue
        # Preprocess to strip parameter noise
        cleaned_line = preprocess_log_line(line)
        result = miner.add_log_message(cleaned_line)
        cluster_id = result["cluster_id"]
        clusters.setdefault(cluster_id, []).append(cleaned_line)

    nodes: list[LogNode] = []
    for cluster in miner.drain.clusters:
        lines = clusters.get(cluster.cluster_id, [])
        template = cluster.get_template()
        
        # Stub version: template name and count only
        stub = f"LOG TEMPLATE: {template} (occurred {len(lines)} times) - [collapsed: query Stage 7 to recover samples]"
        
        node = LogNode(
            id=f"log_cluster_{cluster.cluster_id}",
            name=template,
            template=template,
            count=len(lines),
            sample_lines=lines[:max_samples_per_cluster],
            token_estimate=len(template.split()) + max_samples_per_cluster * 5,
            stub=stub
        )
        nodes.append(node)

    return nodes

"""
Stage 2 (logs): Structural Layer.

Uses Drain3 to cluster log lines into templates, e.g.
  "User <ID> failed login at <TS>"  x 47 occurrences
Collapses repeats into {pattern, count, sample_lines} instead of keeping
every raw line - this alone is usually 30-40% of your compression win,
before any AI-based pruning happens.
"""
import hashlib
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

    def content_hash(self) -> str:
        return hashlib.sha256(self.template.encode()).hexdigest()


def build_log_templates(raw_logs: str, max_samples_per_cluster: int = 2) -> list[LogNode]:
    config = TemplateMinerConfig()
    config.load(None)  # use library defaults; tune drain3.ini for real data
    miner = TemplateMiner(config=config)

    clusters: dict[int, list[str]] = {}

    for line in raw_logs.splitlines():
        line = line.strip()
        if not line:
            continue
        result = miner.add_log_message(line)
        cluster_id = result["cluster_id"]
        clusters.setdefault(cluster_id, []).append(line)

    nodes: list[LogNode] = []
    for cluster in miner.drain.clusters:
        lines = clusters.get(cluster.cluster_id, [])
        template = cluster.get_template()
        node = LogNode(
            id=f"log_cluster_{cluster.cluster_id}",
            name=template,
            template=template,
            count=len(lines),
            sample_lines=lines[:max_samples_per_cluster],
            token_estimate=len(template.split()) + max_samples_per_cluster * 5,
        )
        nodes.append(node)

    return nodes

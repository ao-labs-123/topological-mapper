from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Node:
    id: str
    label: str
    category: str
    w5h1_attributes: dict[str, str] = field(default_factory=dict)
    resolution_state: str | None = None


@dataclass
class TopologicalGraph:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Any] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

class GraphBuilder:
    @classmethod
    def build_graph(cls, particle_data: list, log_data: list) -> TopologicalGraph:
        graph = TopologicalGraph()
        
        # log.json の各インプットを ID やインデックスで紐付け
        for index, p in enumerate(particle_data):
            
            # 1. particles.json からノードの基本構造を作成
            node = Node(
                id=p["id"],
                label=p["label"],
                category="Entity" if p["entity_type"] == "Agent" else "Event"
            )

            # 2. log.json の情報を使って 5W1H (When / Where) や State を補完・確定
            log_item = log_data[index] if index < len(log_data) else {}
            input_text = log_item.get("input", "")
            
            # (例) log.json の文脈から Time / Location の制約や属性を確定させる判定 logic
            if "yesterday" in input_text.lower():
                node.w5h1_attributes["when"] = "yesterday"
                node.resolution_state = "Determined"

            graph.nodes.append(node)

        # 3. log.json の Stage フラグを元に Constraint 射や Action 射を正確に配線
        # (例: Stage 4 が Essential なら Constraint 射を張る)

        return graph

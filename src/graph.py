# src/graph.py

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any

@dataclass
class Node:
    id: str             # 粒子ID
    label: str          # テキスト表現
    category: str       # Entity (実体) または Event (事象)

@dataclass
class Edge:
    id: str             # 射のID
    source: str         # 始点ノードID (Domain)
    target: str         # 終点ノードID (Codomain)
    morphism_type: str  # Relation / Action / Cause / Constraint

@dataclass
class TopologicalGraph:
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GraphBuilder:
    @classmethod
    def build_graph(cls, particle_data: List[Dict[str, Any]], log_data: Any = None) -> TopologicalGraph:
        graph = TopologicalGraph()

        cause_nodes = []
        effect_nodes = []

        # 1. 粒子を Node (Entity / Event) として展開
        for p in particle_data:
            p_type = p.get("entity_type", "")

            # Agent は Entity 圏、Cause/Effect は Event 圏へ分類
            category = "Entity" if p_type == "Agent" else "Event"

            node = Node(
                id=p["id"],
                label=p["label"],
                category=category
            )
            graph.nodes.append(node)

            # 因果関係の配線用にIDを保持
            if p_type == "Cause":
                cause_nodes.append(node)
            elif p_type == "Effect":
                effect_nodes.append(node)

        # 2. Morphism (射 / Edge) の自動配線ロジック
        # Cause 粒子と Effect 粒子が存在する場合、その間に Cause 射（ワイヤー）を張る
        for cause in cause_nodes:
            for effect in effect_nodes:
                edge = Edge(
                    id=f"e_cause_{cause.id}_{effect.id}",
                    source=cause.id,
                    target=effect.id,
                    morphism_type="Cause"
                )
                graph.edges.append(edge)

        # 3. ログデータが存在する場合は将来の拡張用に保持しておく
        if log_data is not None:
            _ = log_data

        return graph

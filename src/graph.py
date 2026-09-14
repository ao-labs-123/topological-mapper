from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class Node:
    id: str             # 粒子ID (例: "p_agent_f06dbc")
    label: str          # テキスト (例: "I", "you helped")
    category: str       # "Entity" (Who/Subject) か "Event" (What/Where/Why...) か

@dataclass
class Edge:
    id: str             # 射のID
    source: str         # 始点ノードのID (Domain)
    target: str         # 終点ノードのID (Codomain)
    morphism_type: str  # "Relation", "Action", "Cause", "Constraint"

@dataclass
class TopologicalGraph:
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)

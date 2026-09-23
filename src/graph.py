# src/graph.py

import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

@dataclass
class Node:
    id: str                             # 粒子ID
    label: str                          # 表示テキスト
    category: str                       # "Entity" または "Event"
    resolution_state: str = "Unspecified"
    attributes: Dict[str, str] = field(default_factory=dict)

@dataclass
class Edge:
    id: str                             # 射のID
    source: str                         # 始点ノードID
    target: str                         # 終点ノードID
    morphism_type: str                  # "Action", "Cause", "Constraint"
    detail: str = ""

@dataclass
class TopologicalGraph:
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GraphBuilder:
    @classmethod
    def build_graph(cls, particle_data: List[Dict[str, Any]], log_data: List[Dict[str, Any]]) -> TopologicalGraph:
        graph = TopologicalGraph()
        
        # 粒子データのインデックス化（IDベース）
        particle_map = {p.get("id"): p for p in particle_data}

        # ---------------------------------------------------------
        # 1. 粒子の空間構築（Node の完全局所化生成）
        # ---------------------------------------------------------
        for p in particle_data:
            p_id = p.get("id", "")
            p_label = p.get("label", "")
            p_type = p.get("entity_type", "")
            
            category = "Entity" if p_type == "Agent" else "Event"
            
            w5h1 = {
                "who": "Unspecified",
                "what": "Unspecified",
                "when": "Unspecified",
                "where": "Unspecified",
                "why": "Unspecified",
                "how": "Unspecified"
            }
            
            is_valid_label = p_label.lower() not in ["unknown", "none", "", "null"]
            
            if category == "Entity":
                if is_valid_label:
                    w5h1["who"] = p_label
            else:
                if is_valid_label:
                    w5h1["what"] = p_label

            # Node の基礎を登録
            node = Node(
                id=p_id,
                label=p_label,
                category=category,
                resolution_state="Unspecified",
                attributes=w5h1
            )
            graph.nodes.append(node)

        # ---------------------------------------------------------
        # 2. 文脈（log_data）ごとの局所評価と Edge (Morphism) 結線
        # ---------------------------------------------------------
        # log_data と particle_data をインデックス(idx)で1対1に完全同調させる
        for idx, log_item in enumerate(log_data):
            if idx >= len(graph.nodes):
                break
            
            current_node = graph.nodes[idx] # インデックスで対象ノードを直接特定（表記揺れによる取り違いを防止）
            input_text = log_item.get("input", "")

            # --- 2-A. 属性の局所補完 (単語単体ではなく前置詞句レベルで誤検知防止) ---
            when_match = re.search(r'\b(yesterday|today|tomorrow|after|before|now)\b', input_text, re.I)
            current_node.attributes["when"] = when_match.group(0) if when_match else "Unspecified"

            where_match = re.search(r'\b(at|in|on)\s+(the\s+\w+|\w+)', input_text, re.I)
            current_node.attributes["where"] = where_match.group(0) if where_match else "Unspecified"

            # 「by」単体ではなく「by him」などの句で拾うよう修正
            how_match = re.search(r'\b(by\s+\w+|with\s+\w+|through\s+\w+|quickly)\b', input_text, re.I)
            current_node.attributes["how"] = how_match.group(0) if how_match else "Unspecified"

            # Determined / Unspecified の再判定
            has_identity = (current_node.attributes["who"] != "Unspecified") or (current_node.attributes["what"] != "Unspecified")
            current_node.resolution_state = "Determined" if has_identity else "Unspecified"

            # --- 2-B. 局所 Cause 射の結線 (Stage 3) ---
            stage3 = log_item.get("stage3")
            if stage3 and isinstance(stage3, dict) and "structure" in stage3:
                struct = stage3["structure"]
                cause_label = struct.get("cause")
                effect_label = struct.get("effect")

                src = next((n for n in graph.nodes if n.label == cause_label), None)
                tgt = next((n for n in graph.nodes if n.label == effect_label), None)

                if src and tgt:
                    graph.edges.append(
                        Edge(
                            id=f"e_cause_{src.id}_{tgt.id}",
                            source=src.id,
                            target=tgt.id,
                            morphism_type="Cause",
                            detail="Primary Cause"
                        )
                    )

            # --- 2-C. 局所 Constraint 射の結線 (自身へのピンポイント結線) ---
            stage4 = log_item.get("stage4")
            is_spatial_temporal_relative = bool(re.search(r'\b(where|when)\b', input_text, re.I)) and ("where" in input_text or "when" in input_text)

            if (stage4 and isinstance(stage4, dict) and stage4.get("decision") == "Essential") or (is_spatial_temporal_relative and stage4):
                detail_msg = "Spatial/Temporal Constraint" if is_spatial_temporal_relative else "Defining Clause Constraint"
                graph.edges.append(
                    Edge(
                        id=f"e_constraint_{current_node.id}",
                        source=current_node.id,
                        target=current_node.id,
                        morphism_type="Constraint",
                        detail=detail_msg
                    )
                )

            stage5 = log_item.get("stage5")
            if stage5 and isinstance(stage5, dict) and "Actor:" in stage5.get("result", ""):
                graph.edges.append(
                    Edge(
                        id=f"e_passive_{current_node.id}",
                        source=current_node.id,
                        target=current_node.id,
                        morphism_type="Constraint",
                        detail="Passive Receiver Constraint"
                    )
                )

        # ---------------------------------------------------------
        # 3. Action 射の結線 (同文脈内の Entity ──Action──> Event)
        # ---------------------------------------------------------
        for idx, log_item in enumerate(log_data):
            stage3 = log_item.get("stage3")
            if stage3 and isinstance(stage3, dict) and "structure" in stage3:
                # idx を使って「その文に対応する Agent ノード」を特定
                if idx < len(graph.nodes):
                    entity_node = graph.nodes[idx]
                    effect_label = stage3["structure"].get("effect")
                    event_node = next((n for n in graph.nodes if n.label == effect_label and n.category == "Event"), None)

                    if entity_node and event_node and entity_node.category == "Entity":
                        edge_id = f"e_action_{entity_node.id}_{event_node.id}"
                        if not any(e.id == edge_id for e in graph.edges):
                            graph.edges.append(
                                Edge(
                                    id=edge_id,
                                    source=entity_node.id,
                                    target=event_node.id,
                                    morphism_type="Action",
                                    detail="Agent of Action"
                                )
                            )
        return graph
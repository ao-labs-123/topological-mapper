# src/graph.py (前半ログの Null 補完対応版)

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
        
        # 1. log.json を input 文テキストでインデックス化
        log_map = {item.get("input", ""): item for item in log_data if item.get("input")}

        # 2. Node の生成と 5W1H 属性の抽出（input 全文に対する絶対フォールバック）
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

            # --- 全一次情報 (log_data) から 5W1H の直接スキャン ---
            for input_text, log_item in log_map.items():
                # 該当する粒子ラベルが含まれる文、または一意の文であれば属性抽出を試みる
                if p_label and (p_label.lower() in input_text.lower() or len(log_data) == len(particle_data)):
                    
                    # When (時間)
                    when_match = re.search(r'\b(yesterday|today|tomorrow|after|before|now)\b', input_text, re.I)
                    if when_match:
                        w5h1["when"] = when_match.group(0)

                    # Where (場所)
                    where_match = re.search(r'\b(at|in|on)\s+(the\s+\w+|\w+)', input_text, re.I)
                    if where_match:
                        w5h1["where"] = where_match.group(0)

                    # How (手段・態)
                    how_match = re.search(r'\b(by|with|through|quickly)\b', input_text, re.I)
                    if how_match:
                        w5h1["how"] = how_match.group(0)

            # 判定: Who / What に加え、When / Where 等が埋まっても Determined に昇格
            has_substance = (w5h1["who"] != "Unspecified") or (w5h1["what"] != "Unspecified")
            resolution_state = "Determined" if has_substance else "Unspecified"

            node = Node(
                id=p_id,
                label=p_label,
                category=category,
                resolution_state=resolution_state,
                attributes=w5h1
            )
            graph.nodes.append(node)

        # 3. Morphism (射) の配線処理
        entities = [n for n in graph.nodes if n.category == "Entity"]
        events = [n for n in graph.nodes if n.category == "Event"]

        # A. Action 射 (Entity ──Action──> Event)
        for entity in entities:
            if entity.resolution_state == "Determined":
                for event in events:
                    graph.edges.append(
                        Edge(
                            id=f"e_action_{entity.id}_{event.id}",
                            source=entity.id,
                            target=event.id,
                            morphism_type="Action",
                            detail="Agent of Action"
                        )
                    )

        # B. Cause & Constraint 射 (log.json の各 Stage フラグまたは input 条件から動的生成)
        for log_item in log_data:
            input_text = log_item.get("input", "")

            # 1) Stage 3 由来の因果射 (Cause)
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

            # 2) Stage 4 由来 または 構文パターン由来の制約射 (Constraint)
            stage4 = log_item.get("stage4")
            # 「where/when」による場所・時間の関係節が含まれる場合も Constraint 射を張る
            is_spatial_temporal_relative = bool(re.search(r'\b(where|when)\b', input_text, re.I))

            if (stage4 and isinstance(stage4, dict) and stage4.get("decision") == "Essential") or is_spatial_temporal_relative:
                agent_label = log_item.get("stage1", {}).get("agent")
                tgt = next((n for n in graph.nodes if n.label == agent_label), None)
                if tgt:
                    detail_msg = "Spatial/Temporal Constraint" if is_spatial_temporal_relative else "Defining Clause Constraint"
                    graph.edges.append(
                        Edge(
                            id=f"e_constraint_{tgt.id}",
                            source=tgt.id,
                            target=tgt.id,
                            morphism_type="Constraint",
                            detail=detail_msg
                        )
                    )

            # 3) Stage 5 由来の受動制約
            stage5 = log_item.get("stage5")
            if stage5 and isinstance(stage5, dict) and "Actor:" in stage5.get("result", ""):
                agent_label = log_item.get("stage1", {}).get("agent")
                tgt = next((n for n in graph.nodes if n.label == agent_label), None)
                if tgt:
                    graph.edges.append(
                        Edge(
                            id=f"e_passive_{tgt.id}",
                            source=tgt.id,
                            target=tgt.id,
                            morphism_type="Constraint",
                            detail="Passive Receiver Constraint"
                        )
                    )

        return graph

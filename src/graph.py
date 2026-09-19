# src/graph.py

import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

@dataclass
class Node:
    id: str                             # 粒子ID (例: "p_agent_f06dbc")
    label: str                          # 表示テキスト
    category: str                       # "Entity" (実体) または "Event" (事象)
    resolution_state: str = "Unspecified" # "Determined" または "Unspecified"
    attributes: Dict[str, str] = field(default_factory=dict) # 5W1H 属性

@dataclass
class Edge:
    id: str                             # 射 (Morphism) のユニークID
    source: str                         # 始点ノードID (Domain)
    target: str                         # 終点ノードID (Codomain)
    morphism_type: str                  # "Action", "Cause", "Constraint", "Relation"
    detail: str = ""                    # 一次情報由来の詳細・条件ラベル

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
        
        # 1. log_data を入力文字列 (input) や構造で検索できるようにインデックス化
        log_map = {}
        for item in log_data:
            input_text = item.get("input", "")
            if input_text:
                log_map[input_text] = item

        # 2. particle.json と log.json から Node (Entity / Event) と 5W1H 属性を構築
        for p in particle_data:
            p_id = p.get("id", "")
            p_label = p.get("label", "")
            p_type = p.get("entity_type", "")
            
            # Agent は Entity 圏、Cause / Effect / その他は Event 圏
            category = "Entity" if p_type == "Agent" else "Event"
            
            # 5W1H 属性の特定ロジック (Determined vs Unspecified)
            w5h1 = {
                "who": "Unspecified",
                "what": "Unspecified",
                "when": "Unspecified",
                "where": "Unspecified",
                "why": "Unspecified",
                "how": "Unspecified"
            }
            
            # Label の有無による基本判定
            is_valid_label = p_label.lower() not in ["unknown", "none", "", "null"]
            
            if category == "Entity":
                if is_valid_label:
                    w5h1["who"] = p_label
            else:
                if is_valid_label:
                    w5h1["what"] = p_label

            # 一次情報 (log.json) から Time (When) / Space (Where) / Manner (How) を抽出
            for input_text, log_item in log_map.items():
                if p_label and p_label.lower() in input_text.lower():
                    # 時間の抽出 (When)
                    when_match = re.search(r'\b(yesterday|today|tomorrow|after|before|now)\b', input_text, re.I)
                    if when_match:
                        w5h1["when"] = when_match.group(0)

                    # 場所の抽出 (Where)
                    where_match = re.search(r'\b(at|in|on)\s+(the\s+\w+|\w+)', input_text, re.I)
                    if where_match:
                        w5h1["where"] = where_match.group(0)

                    # 手段・状態の抽出 (How)
                    how_match = re.search(r'\b(by|with|through)\s+([\w\s]+)', input_text, re.I)
                    if how_match:
                        w5h1["how"] = how_match.group(0)

            # Node の特定状態 (resolution_state) の決定
            # Who または What が埋まっていれば Determined
            is_determined = (w5h1["who"] != "Unspecified") or (w5h1["what"] != "Unspecified")
            resolution_state = "Determined" if is_determined else "Unspecified"

            node = Node(
                id=p_id,
                label=p_label,
                category=category,
                resolution_state=resolution_state,
                attributes=w5h1
            )
            graph.nodes.append(node)

        # 3. Morphism (射 / Edge) の自動結線ロジック
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

        # B. Cause / Constraint 射 (log.json の Stage 3 / 4 / 5 フラグに基づく配線)
        for log_item in log_data:
            # Stage 3: Cause (因果射)
            stage3 = log_item.get("stage3")
            if stage3 and isinstance(stage3, dict) and "structure" in stage3:
                struct = stage3["structure"]
                cause_label = struct.get("cause")
                effect_label = struct.get("effect")

                source_node = next((n for n in graph.nodes if n.label == cause_label), None)
                target_node = next((n for n in graph.nodes if n.label == effect_label), None)

                if source_node and target_node:
                    graph.edges.append(
                        Edge(
                            id=f"e_cause_{source_node.id}_{target_node.id}",
                            source=source_node.id,
                            target=target_node.id,
                            morphism_type="Cause",
                            detail="Primary Cause"
                        )
                    )

            # Stage 4: Constraint (限定節・文脈制約)
            stage4 = log_item.get("stage4")
            if stage4 and isinstance(stage4, dict) and stage4.get("decision") == "Essential":
                agent_label = log_item.get("stage1", {}).get("agent")
                target_node = next((n for n in graph.nodes if n.label == agent_label), None)
                if target_node:
                    graph.edges.append(
                        Edge(
                            id=f"e_constraint_defining_{target_node.id}",
                            source=target_node.id,
                            target=target_node.id,
                            morphism_type="Constraint",
                            detail="Defining Relative Clause (Essential)"
                        )
                    )

            # Stage 5: Constraint (受動態/作用者制約)
            stage5 = log_item.get("stage5")
            if stage5 and isinstance(stage5, dict) and "Actor:" in stage5.get("result", ""):
                agent_label = log_item.get("stage1", {}).get("agent")
                target_node = next((n for n in graph.nodes if n.label == agent_label), None)
                if target_node:
                    graph.edges.append(
                        Edge(
                            id=f"e_constraint_passive_{target_node.id}",
                            source=target_node.id,
                            target=target_node.id,
                            morphism_type="Constraint",
                            detail="Passive Receiver Constraint"
                        )
                    )

        return graph

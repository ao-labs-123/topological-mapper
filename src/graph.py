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
    constraint_type: str = ""          # "Condition", "State" など、Constraint の内部分類

@dataclass
class TopologicalGraph:
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GraphBuilder:
    EVENT_STOP_WORDS = {
        "a", "an", "the", "i", "you", "he", "she", "they", "we", "it",
        "am", "is", "are", "was", "were", "be", "been", "being",
    }

    @classmethod
    def _find_event_node(cls, graph: TopologicalGraph, event_label: str) -> Optional[Node]:
        event_node = next(
            (node for node in graph.nodes
             if node.category == "Event" and node.label.casefold() == event_label.casefold()),
            None,
        )
        if event_node:
            return event_node

        event_words = set(re.findall(r"\b[a-z]+\b", event_label.casefold())) - cls.EVENT_STOP_WORDS
        if not event_words:
            return None

        matches = [
            node for node in graph.nodes
            if node.category == "Event"
            and event_words.issubset(
                set(re.findall(r"\b[a-z]+\b", node.label.casefold())) - cls.EVENT_STOP_WORDS
            )
        ]
        return matches[0] if len(matches) == 1 else None

    @classmethod
    def _find_constraint_target(cls, graph: TopologicalGraph, current_node: Node, log_item: Dict[str, Any], idx: int) -> Optional[Node]:
        stage3 = log_item.get("stage3")
        if stage3 and isinstance(stage3, dict) and "structure" in stage3:
            struct = stage3["structure"]
            candidate_labels = []
            for key in ("effect", "cause"):
                label = struct.get(key)
                if label:
                    candidate_labels.append(str(label))

            for label in candidate_labels:
                event_node = cls._find_event_node(graph, label)
                if event_node and event_node.id != current_node.id:
                    return event_node

        # ルール: 明示的なイベント関係がない場合は、Constraint を「最初の Event」へ
        # 勝手に寄せない。曖昧な Constraint は生成しない。
        return None

    @classmethod
    def _add_particle_constraint_edges(cls, graph: TopologicalGraph, particle_data: List[Dict[str, Any]]) -> None:
        nodes_by_id = {node.id: node for node in graph.nodes}

        for particle in particle_data:
            source = nodes_by_id.get(particle.get("id"))
            constraints = particle.get("constraints") or []
            if isinstance(constraints, str):
                constraints = [constraints]
            constraints = [str(value).strip() for value in constraints if str(value).strip()]
            if source is None or not constraints:
                continue

            entity_type = particle.get("entity_type", "")
            target = None
            constraint_type = f"{entity_type}Condition"
            detail = "; ".join(constraints)

            if entity_type == "Cause":
                matching_effects = [
                    candidate
                    for candidate in particle_data
                    if candidate.get("entity_type") == "Effect"
                    and set(constraints).intersection(candidate.get("constraints") or [])
                ]
                if len(matching_effects) == 1:
                    target = nodes_by_id.get(matching_effects[0].get("id"))
            else:
                event_label = (particle.get("properties") or {}).get("event")
                if event_label:
                    target = cls._find_event_node(graph, str(event_label))

            if target is None or target.id == source.id:
                continue

            edge_id = f"e_particle_constraint_{source.id}_{target.id}"
            if any(edge.id == edge_id for edge in graph.edges):
                continue
            graph.edges.append(
                Edge(
                    id=edge_id,
                    source=source.id,
                    target=target.id,
                    morphism_type="Constraint",
                    detail=detail,
                    constraint_type=constraint_type,
                )
            )

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
                constraints = p.get("constraints") or []
                if isinstance(constraints, str):
                    constraints = [constraints]
                for constraint in constraints:
                    agent_match = re.search(
                        r"\bAgent:\s*(.+?)(?:\s*\+\s*|$)", str(constraint)
                    )
                    if agent_match:
                        w5h1["agent"] = agent_match.group(1).strip()
                        break

            # Node の基礎を登録
            node = Node(
                id=p_id,
                label=p_label,
                category=category,
                resolution_state="Unspecified",
                attributes=w5h1
            )
            graph.nodes.append(node)

        cls._add_particle_constraint_edges(graph, particle_data)

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
                relation = struct.get("relation")
                if relation in ("Manner", "Temporal"):
                    source = next(
                        (node for node in graph.nodes if node.label.casefold() == struct.get("context", "").casefold()),
                        None,
                    )
                    target = cls._find_event_node(graph, struct.get("event", ""))
                    if source and target:
                        edge_id = f"e_{relation.lower()}_{source.id}_{target.id}"
                        if not any(edge.id == edge_id for edge in graph.edges):
                            graph.edges.append(
                                Edge(
                                    id=edge_id,
                                    source=source.id,
                                    target=target.id,
                                    morphism_type=relation,
                                    detail=f"{relation} relation ({struct.get('marker', '')})",
                                )
                            )

                cause_label = struct.get("cause")
                effect_label = struct.get("effect")

                cause_candidates = [
                    node for node in graph.nodes
                    if node.label.casefold() == str(cause_label).casefold()
                    and particle_map.get(node.id, {}).get("entity_type") == "Cause"
                ]
                effect_candidates = [
                    node for node in graph.nodes
                    if node.label.casefold() == str(effect_label).casefold()
                    and particle_map.get(node.id, {}).get("entity_type") == "Effect"
                ]
                matching_pairs = [
                    (cause_node, effect_node)
                    for cause_node in cause_candidates
                    for effect_node in effect_candidates
                    if set(particle_map[cause_node.id].get("constraints") or []).intersection(
                        particle_map[effect_node.id].get("constraints") or []
                    )
                ]

                if len(matching_pairs) == 1:
                    src, tgt = matching_pairs[0]
                elif len(cause_candidates) == 1 and len(effect_candidates) == 1:
                    src, tgt = cause_candidates[0], effect_candidates[0]
                else:
                    src, tgt = None, None

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

            # --- 2-C. 局所 Constraint 射の結線 (自己参照ではなく関連する Event へ接続) ---
            stage4 = log_item.get("stage4")
            is_spatial_temporal_relative = bool(re.search(r'\b(where|when)\b', input_text, re.I)) and ("where" in input_text or "when" in input_text)

            if (stage4 and isinstance(stage4, dict) and stage4.get("decision") == "Essential") or (is_spatial_temporal_relative and stage4):
                detail_msg = "Spatial/Temporal Constraint" if is_spatial_temporal_relative else "Defining Clause Constraint"
                constraint_kind = "SpatialTemporalCondition" if is_spatial_temporal_relative else "ClauseCondition"
                target_node = cls._find_constraint_target(graph, current_node, log_item, idx)
                if target_node:
                    edge_id = f"e_constraint_{current_node.id}_{target_node.id}"
                    if not any(edge.id == edge_id for edge in graph.edges):
                        graph.edges.append(
                            Edge(
                                id=edge_id,
                                source=current_node.id,
                                target=target_node.id,
                                morphism_type="Constraint",
                                detail=detail_msg,
                                constraint_type=constraint_kind,
                            )
                        )

            stage5 = log_item.get("stage5")
            if stage5 and isinstance(stage5, dict) and "Actor:" in stage5.get("result", ""):
                target_node = cls._find_constraint_target(graph, current_node, log_item, idx)
                if target_node:
                    edge_id = f"e_passive_{current_node.id}_{target_node.id}"
                    if not any(edge.id == edge_id for edge in graph.edges):
                        graph.edges.append(
                            Edge(
                                id=edge_id,
                                source=current_node.id,
                                target=target_node.id,
                                morphism_type="Constraint",
                                detail="Passive Receiver Constraint",
                                constraint_type="PassiveState",
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
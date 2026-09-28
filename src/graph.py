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
        matches = [
            node for node in graph.nodes
            if node.category == "Event"
            and node.label.casefold() == event_label.casefold()
        ]
        return matches[0] if len(matches) == 1 else None

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
                resolution_state="Determined" if is_valid_label else "Unspecified",
                attributes=w5h1
            )
            graph.nodes.append(node)

        cls._add_particle_constraint_edges(graph, particle_data)

        # ---------------------------------------------------------
        # 2. 文脈（log_data）ごとの局所評価と Edge (Morphism) 結線
        # ---------------------------------------------------------
        for log_item in log_data:
            input_text = log_item.get("input", "")

            # --- 2-A. Stage 3 が明示するイベントに文脈属性を付与 ---
            when_match = re.search(r'\b(yesterday|today|tomorrow|after|before|now)\b', input_text, re.I)
            where_match = re.search(r'\b(at|in|on)\s+(the\s+\w+|\w+)', input_text, re.I)
            how_match = re.search(r'\b(by\s+\w+|with\s+\w+|through\s+\w+|quickly)\b', input_text, re.I)
            stage3_structure = (log_item.get("stage3") or {}).get("structure") or {}
            event_labels = {
                str(stage3_structure[key]).casefold()
                for key in ("cause", "effect", "event", "context")
                if stage3_structure.get(key)
            }
            stage1 = log_item.get("stage1") or {}
            stage2 = log_item.get("stage2") or {}
            agent_label = stage2.get("resolved_agent") or stage1.get("agent")
            context_values = {
                "when": when_match.group(0) if when_match else None,
                "where": where_match.group(0) if where_match else None,
                "how": how_match.group(0) if how_match else None,
            }
            if event_labels and any(context_values.values()):
                for event_label in event_labels:
                    event_candidates = [
                        node for node in graph.nodes
                        if node.category == "Event"
                        and node.label.casefold() == event_label
                        and (
                            not agent_label
                            or f"agent: {str(agent_label).casefold()}"
                            in " ".join(particle_map.get(node.id, {}).get("constraints") or []).casefold()
                        )
                    ]
                    if len(event_candidates) != 1:
                        continue
                    for attribute, value in context_values.items():
                        if value:
                            event_candidates[0].attributes[attribute] = value

            # --- 2-B. 局所 Cause 射の結線 (Stage 3) ---
            stage3 = log_item.get("stage3")
            if stage3 and isinstance(stage3, dict) and "structure" in stage3:
                struct = stage3["structure"]
                relation = struct.get("relation")
                if relation in ("Manner", "Temporal"):
                    source = cls._find_event_node(graph, str(struct.get("context", "")))
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
                    if cause_label
                    and node.label.casefold() == str(cause_label).casefold()
                    and particle_map.get(node.id, {}).get("entity_type") == "Cause"
                ]
                effect_candidates = [
                    node for node in graph.nodes
                    if effect_label
                    and node.label.casefold() == str(effect_label).casefold()
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

        # ---------------------------------------------------------
        # 3. Action 射の結線 (同文脈内の Entity ──Action──> Event)
        # ---------------------------------------------------------
        for log_item in log_data:
            stage3 = log_item.get("stage3")
            if stage3 and isinstance(stage3, dict) and "structure" in stage3:
                structure = stage3["structure"]
                effect_label = structure.get("effect")
                stage1 = log_item.get("stage1") or {}
                stage2 = log_item.get("stage2") or {}
                agent_label = stage2.get("resolved_agent") or stage1.get("agent")
                if not effect_label or not agent_label:
                    continue

                event_candidates = [
                    node for node in graph.nodes
                    if node.category == "Event"
                    and node.label.casefold() == str(effect_label).casefold()
                    and particle_map.get(node.id, {}).get("entity_type") == "Effect"
                ]
                entity_candidates = [
                    node for node in graph.nodes
                    if node.category == "Entity"
                    and node.label.casefold() == str(agent_label).casefold()
                ]
                if len(event_candidates) != 1 or len(entity_candidates) != 1:
                    continue

                event_node = event_candidates[0]
                entity_node = entity_candidates[0]

                edge_id = f"e_action_{entity_node.id}_{event_node.id}"
                if not any(edge.id == edge_id for edge in graph.edges):
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
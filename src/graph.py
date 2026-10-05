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

    @staticmethod
    def _resolve_particle_node(
        graph: TopologicalGraph,
        particle_map: Dict[str, Dict[str, Any]],
        particle_id: Any,
        expected_type: Optional[str],
    ) -> Optional[Node]:
        if not isinstance(particle_id, str) or not particle_id.strip():
            return None
        matches = [node for node in graph.nodes if node.id == particle_id]
        if len(matches) != 1:
            return None

        node = matches[0]
        if expected_type:
            expected_category = "Entity" if expected_type == "Agent" else "Event"
            if (
                node.category != expected_category
                or particle_map.get(node.id, {}).get("entity_type") != expected_type
            ):
                return None
        return node

    @classmethod
    def _resolve_stage3_particle_node(
        cls,
        graph: TopologicalGraph,
        particle_map: Dict[str, Dict[str, Any]],
        structure: Dict[str, Any],
        id_key: str,
        label_key: str,
        expected_type: str,
        agent: Any = None,
        allow_label_fallback: bool = False,
    ) -> Optional[Node]:
        particle_id = structure.get(id_key)
        if isinstance(particle_id, str) and particle_id.strip():
            node = cls._resolve_particle_node(graph, particle_map, particle_id, expected_type)
            if node:
                return node
            if not allow_label_fallback:
                return None
        elif id_key in structure and particle_id not in (None, ""):
            return None

        label = structure.get(label_key)
        if not isinstance(label, str) or not label.strip():
            return None

        candidates = []
        for node in graph.nodes:
            particle = particle_map.get(node.id, {})
            particle_label = particle.get("label")
            if (
                particle.get("entity_type") == expected_type
                and isinstance(particle_label, str)
                and particle_label.strip().casefold() == label.strip().casefold()
            ):
                candidates.append(node)

        if len(candidates) == 1:
            return candidates[0]
        if not isinstance(agent, str) or not agent.strip():
            return None

        matching_candidates = []
        for node in candidates:
            constraints = particle_map.get(node.id, {}).get("constraints") or []
            if isinstance(constraints, str):
                constraints = [constraints]
            for constraint in constraints:
                agent_match = re.search(r"\bAgent:\s*(.+?)(?:\s*\+\s*|$)", str(constraint))
                if agent_match and agent_match.group(1).strip().casefold() == agent.strip().casefold():
                    matching_candidates.append(node)
                    break
        return matching_candidates[0] if len(matching_candidates) == 1 else None

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

            properties = particle.get("properties") or {}
            if entity_type == "Cause":
                target_particle_id = particle.get("target_particle_id")
                target_type = "Effect"
            else:
                target_particle_id = (
                    properties.get("event_particle_id")
                    or particle.get("target_particle_id")
                )
                target_type = "Effect" if properties.get("event_particle_id") else None
            target = cls._resolve_particle_node(
                graph, {item.get("id"): item for item in particle_data},
                target_particle_id, target_type
            )

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
            properties = p.get("properties") or {}

            if (
                p_type == "Morphology"
                and not p.get("target_particle_id")
                and not properties.get("event_particle_id")
            ):
                continue
            
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
            context_values = {
                "when": when_match.group(0) if when_match else None,
                "where": where_match.group(0) if where_match else None,
                "how": how_match.group(0) if how_match else None,
            }
            stage2 = log_item.get("stage2") or {}
            stage2_structure = stage2.get("structure") if isinstance(stage2, dict) else None
            if not isinstance(stage2_structure, dict):
                stage2_structure = {}
            stage3 = log_item.get("stage3") or {}
            stage3_structure = stage3.get("structure") if isinstance(stage3, dict) else None
            if not isinstance(stage3_structure, dict):
                stage3_structure = {}
            cause_structure = (
                stage2_structure
                if stage2_structure.get("relation") == "CauseEffect"
                or stage2_structure.get("cause_particle_id")
                or stage2_structure.get("effect_particle_id")
                else stage3_structure
            )
            allow_cause_label_fallback = cause_structure is stage2_structure
            stage5 = log_item.get("stage5") or {}
            if isinstance(stage5, dict):
                stage5_target_ids = (
                    stage5.get("target_particle_id"),
                    stage2_structure.get("effect_particle_id"),
                    stage3_structure.get("effect_particle_id"),
                    stage3_structure.get("event_particle_id"),
                )
                stage5_event = None
                for particle_id in stage5_target_ids:
                    candidate = cls._resolve_particle_node(graph, particle_map, particle_id, None)
                    if candidate and candidate.category == "Event":
                        stage5_event = candidate
                        break
                if stage5_event is None:
                    stage5_event = cls._resolve_stage3_particle_node(
                        graph,
                        particle_map,
                        cause_structure,
                        "effect_particle_id",
                        "effect",
                        "Effect",
                        allow_label_fallback=allow_cause_label_fallback,
                    )
                if stage5_event is None:
                    frame = stage5.get("frame")
                    frame_what = frame.get("what") if isinstance(frame, dict) else None
                    what_candidates = [
                        node
                        for node in graph.nodes
                        if particle_map.get(node.id, {}).get("entity_type") == "What"
                        and isinstance(frame_what, str)
                        and str(particle_map[node.id].get("label", "")).strip().casefold()
                        == frame_what.strip().casefold()
                    ]
                    if len(what_candidates) == 1:
                        stage5_event = what_candidates[0]
                if stage5_event:
                    process = stage5.get("process")
                    result = stage5.get("result")
                    if isinstance(process, str) and process.strip():
                        stage5_event.attributes["stage5_process"] = process
                    if isinstance(result, str) and result.strip():
                        stage5_event.attributes["stage5_result"] = result
                    frame = stage5.get("frame")
                    if isinstance(frame, dict):
                        for attribute in ("who", "what", "when", "where", "why", "how"):
                            value = frame.get(attribute)
                            if isinstance(value, str) and value.strip():
                                stage5_event.attributes[attribute] = value

            stage1 = log_item.get("stage1") or {}
            stage1_agent = stage1.get("agent") if isinstance(stage1, dict) else None
            relation = stage3_structure.get("relation")
            context_node = None
            if relation in ("Manner", "Temporal"):
                context_node = cls._resolve_particle_node(
                    graph,
                    particle_map,
                    stage3_structure.get("context_particle_id"),
                    relation,
                )
            referenced_events = [
                cls._resolve_stage3_particle_node(
                    graph,
                    particle_map,
                    cause_structure,
                    "cause_particle_id",
                    "cause",
                    "Cause",
                    stage1_agent,
                    allow_cause_label_fallback,
                ),
                cls._resolve_stage3_particle_node(
                    graph,
                    particle_map,
                    cause_structure,
                    "effect_particle_id",
                    "effect",
                    "Effect",
                    stage1_agent,
                    allow_cause_label_fallback,
                ),
                cls._resolve_particle_node(graph, particle_map, stage3_structure.get("event_particle_id"), "Effect"),
                context_node,
            ]
            if any(context_values.values()):
                for event_node in {node.id: node for node in referenced_events if node}.values():
                    for attribute, value in context_values.items():
                        if value:
                            event_node.attributes[attribute] = value

            # --- 2-B. Cause / context relation edges ---
            struct = cause_structure
            if struct:
                relation = struct.get("relation")
                if relation in ("Manner", "Temporal"):
                    source = cls._resolve_particle_node(
                        graph, particle_map, struct.get("context_particle_id"), relation
                    )
                    target = cls._resolve_particle_node(
                        graph, particle_map, struct.get("event_particle_id"), "Effect"
                    )
                    if source and target and source.id != target.id:
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

                src = cls._resolve_stage3_particle_node(
                    graph,
                    particle_map,
                    struct,
                    "cause_particle_id",
                    "cause",
                    "Cause",
                    stage1_agent,
                    allow_cause_label_fallback,
                )
                tgt = cls._resolve_stage3_particle_node(
                    graph,
                    particle_map,
                    struct,
                    "effect_particle_id",
                    "effect",
                    "Effect",
                    stage1_agent,
                    allow_cause_label_fallback,
                )

                if src and tgt:
                    edge_id = f"e_cause_{src.id}_{tgt.id}"
                    if not any(edge.id == edge_id for edge in graph.edges):
                        graph.edges.append(
                            Edge(
                                id=edge_id,
                                source=src.id,
                                target=tgt.id,
                                morphism_type="Cause",
                                detail="Primary Cause"
                            )
                        )

        # ---------------------------------------------------------
        # 3. 明示的な Stage 4/5 ID 参照から Constraint 射を結線
        # ---------------------------------------------------------
        for log_item in log_data:
            for stage_name, detail in (
                ("stage4", "Defining Clause Constraint"),
                ("stage5", "Passive Receiver Constraint"),
            ):
                stage = log_item.get(stage_name) or {}
                if not isinstance(stage, dict):
                    continue
                if stage_name == "stage4" and stage.get("decision") != "Essential":
                    continue
                if stage_name == "stage5":
                    result = stage.get("result")
                    if not isinstance(result, str) or "Actor:" not in result:
                        continue

                source = cls._resolve_particle_node(
                    graph, particle_map, stage.get("source_particle_id"), None
                )
                target = cls._resolve_particle_node(
                    graph, particle_map, stage.get("target_particle_id"), None
                )
                if source is None or target is None or source.id == target.id:
                    continue

                edge_id = f"e_{stage_name}_{source.id}_{target.id}"
                if not any(edge.id == edge_id for edge in graph.edges):
                    graph.edges.append(
                        Edge(
                            id=edge_id,
                            source=source.id,
                            target=target.id,
                            morphism_type="Constraint",
                            detail=detail,
                            constraint_type=stage.get(
                                "constraint_type",
                                "ClauseCondition" if stage_name == "stage4" else "PassiveState",
                            ),
                        )
                    )

        # ---------------------------------------------------------
        # 4. Action 射の結線 (同文脈内の Entity ──Action──> Event)
        # ---------------------------------------------------------
        for log_item in log_data:
            stage1 = log_item.get("stage1") or {}
            stage1_agent = stage1.get("agent") if isinstance(stage1, dict) else None
            stages = (log_item.get("stage2"), log_item.get("stage3"))
            for stage in stages:
                if not isinstance(stage, dict) or not isinstance(stage.get("structure"), dict):
                    continue
                structure = stage["structure"]
                entity_node = cls._resolve_particle_node(
                    graph, particle_map, structure.get("agent_particle_id"), "Agent"
                )
                if entity_node is None and isinstance(stage1_agent, str):
                    agent_candidates = [
                        node
                        for node in graph.nodes
                        if particle_map.get(node.id, {}).get("entity_type") == "Agent"
                        and str(particle_map[node.id].get("label", "")).strip().casefold()
                        == stage1_agent.strip().casefold()
                    ]
                    if len(agent_candidates) == 1:
                        entity_node = agent_candidates[0]
                event_node = cls._resolve_particle_node(
                    graph, particle_map, structure.get("effect_particle_id"), "Effect"
                )
                if event_node is None:
                    event_node = cls._resolve_stage3_particle_node(
                        graph,
                        particle_map,
                        structure,
                        "effect_particle_id",
                        "effect",
                        "Effect",
                        allow_label_fallback=stage is stages[0],
                    )
                if entity_node is None or event_node is None:
                    continue

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
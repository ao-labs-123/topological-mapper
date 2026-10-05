import json

from src.graph import GraphBuilder
from src.upstream_adapter import load_upstream_repo, normalize_upstream_payload
from visualize import (
    _filter_unknown_agent_nodes,
    _is_unknown_agent_node,
    visualize_topological_graph,
)


def test_visualizer_hides_unknown_agent_nodes_only():
    assert _is_unknown_agent_node({"category": "Entity", "label": "Unknown"})
    assert _is_unknown_agent_node({"category": "Entity", "label": "  "})
    assert not _is_unknown_agent_node({"category": "Entity", "label": "I"})
    assert not _is_unknown_agent_node({"category": "Event", "label": "Unknown"})


def test_visualizer_keeps_matching_agent_labels_as_separate_nodes():
    nodes = [
        {"id": "agent-1", "category": "Entity", "label": "I"},
        {"id": "agent-2", "category": "Entity", "label": " i "},
        {"id": "agent-unknown", "category": "Entity", "label": "Unknown"},
        {"id": "event-1", "category": "Event", "label": "I arrived"},
    ]

    display_nodes, node_id_map = _filter_unknown_agent_nodes(nodes)

    assert [node["id"] for node in display_nodes] == ["agent-1", "agent-2", "event-1"]
    assert node_id_map["agent-1"] == "agent-1"
    assert node_id_map["agent-2"] == "agent-2"
    assert "agent-unknown" not in node_id_map


def test_visualizer_shows_stage5_details_in_tooltip_not_node_label(tmp_path):
    graph_path = tmp_path / "graph.json"
    output_path = tmp_path / "index.html"
    graph_path.write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "id": "event-1",
                        "label": "he succeeded",
                        "category": "Event",
                        "attributes": {
                            "what": "he succeeded",
                            "stage5_process": "[Morphology: Base] -> [Category: Action]",
                            "stage5_result": "General action statement.",
                        },
                    }
                ],
                "edges": [],
            }
        ),
        encoding="utf-8",
    )

    visualize_topological_graph(str(graph_path), str(output_path))
    html = (
        output_path.read_text(encoding="utf-8")
        .replace("\\u003c", "<")
        .replace("\\u003e", ">")
    )

    assert "he succeeded [S5: Action]" not in html
    assert "Category</b>: Action" in html
    assert "Interpretation</b>: General action statement." in html
    assert "stage5_process" not in html
    assert "stage5_result" not in html


def test_upstream_stage_data_is_normalized_for_stage3_4_5():
    upstream_payload = {
        "particles": [
            {"id": "agent-1", "label": "I", "entity_type": "Agent"},
            {"id": "event-1", "label": "submit the form", "entity_type": "Event"},
        ],
        "records": [
            {
                "input": "I submit the form at the office",
                "stage3": {"structure": {"effect": "submit the form"}},
                "stage4": {"decision": "Essential", "source_particle_id": "agent-1", "target_particle_id": "event-1"},
                "stage5": {"result": "Actor: I", "source_particle_id": "agent-1", "target_particle_id": "event-1"},
            }
        ],
    }

    particle_data, log_data = normalize_upstream_payload(upstream_payload)

    assert particle_data[0]["id"] == "agent-1"
    assert log_data[0]["stage3"]["structure"]["effect"] == "submit the form"
    assert log_data[0]["stage4"]["target_particle_id"] == "event-1"
    assert log_data[0]["stage5"]["source_particle_id"] == "agent-1"

    graph = GraphBuilder.build_graph(particle_data, log_data)
    constraint_edges = [edge for edge in graph.edges if edge.morphism_type == "Constraint"]
    assert constraint_edges
    assert any(edge.source == "agent-1" and edge.target == "event-1" for edge in constraint_edges)
    event_node = next(node for node in graph.nodes if node.id == "event-1")
    assert event_node.attributes["stage5_result"] == "Actor: I"


def test_upstream_repo_directory_with_data_log_and_particles_is_supported(tmp_path):
    repo_dir = tmp_path / "upstream-repo"
    data_dir = repo_dir / "data"
    data_dir.mkdir(parents=True)

    (repo_dir / "particles.json").write_text(
        json.dumps([
            {"id": "agent-1", "label": "I", "entity_type": "Agent"},
            {"id": "event-1", "label": "submit the form", "entity_type": "Event"},
        ]),
        encoding="utf-8",
    )
    (data_dir / "log.json").write_text(
        json.dumps([
            {
                "input": "I submit the form",
                "stage3": {"structure": {"effect": "submit the form"}},
                "stage4": {"decision": "Essential", "source_particle_id": "agent-1", "target_particle_id": "event-1"},
                "stage5": {"result": "Actor: I", "source_particle_id": "agent-1", "target_particle_id": "event-1"},
            }
        ]),
        encoding="utf-8",
    )

    particle_data, log_data = load_upstream_repo(repo_dir, particle_repo_dir=repo_dir)
    assert particle_data[0]["id"] == "agent-1"
    assert log_data[0]["stage4"]["target_particle_id"] == "event-1"

    graph = GraphBuilder.build_graph(particle_data, log_data)
    assert any(edge.morphism_type == "Constraint" for edge in graph.edges)


def test_new_stage_layout_builds_cause_and_stage5_frame_without_null_errors():
    particle_data = [
        {"id": "agent-1", "label": "He", "entity_type": "Agent"},
        {"id": "cause-1", "label": "I helped", "entity_type": "Cause"},
        {"id": "effect-1", "label": "He succeeded", "entity_type": "Effect"},
    ]
    log_data = [
        {
            "stage1": {"agent": "He"},
            "stage2": {
                "structure": {
                    "relation": "CauseEffect",
                    "cause": "I helped",
                    "effect": "He succeeded",
                    "cause_particle_id": "stale-cause-id",
                    "effect_particle_id": "stale-effect-id",
                }
            },
            "stage3": {"structure": None},
            "stage4": {"structure": {"form": "Base", "verb": "succeeded"}},
            "stage5": {
                "frame": {
                    "who": "He",
                    "what": "succeeded",
                    "when": "Unspecified",
                    "where": "Unspecified",
                    "why": "because I helped",
                    "how": "Unspecified",
                },
                "result": None,
            },
        }
    ]

    graph = GraphBuilder.build_graph(particle_data, log_data)

    assert any(
        edge.morphism_type == "Cause" and edge.source == "cause-1" and edge.target == "effect-1"
        for edge in graph.edges
    )
    assert any(
        edge.morphism_type == "Action" and edge.source == "agent-1" and edge.target == "effect-1"
        for edge in graph.edges
    )
    effect = next(node for node in graph.nodes if node.id == "effect-1")
    assert effect.attributes["who"] == "He"
    assert effect.attributes["what"] == "succeeded"
    assert effect.attributes["why"] == "because I helped"


def test_particle_repo_directory_loads_root_log_json(tmp_path):
    repo_dir = tmp_path / "particle-encapsulation"
    repo_dir.mkdir()

    (repo_dir / "particles.json").write_text(json.dumps([]), encoding="utf-8")
    (repo_dir / "log.json").write_text(
        json.dumps([{"input": "I submitted the form"}]),
        encoding="utf-8",
    )

    particle_data, log_data = load_upstream_repo(particle_repo_dir=repo_dir)

    assert particle_data == []
    assert log_data[0]["input"] == "I submitted the form"


def test_stage4_without_explicit_target_does_not_create_constraint_edge():
    particle_data = [
        {"id": "agent-1", "label": "I", "entity_type": "Agent"},
        {"id": "event-1", "label": "submit the form", "entity_type": "Event"},
    ]
    log_data = [
        {
            "input": "I submit the form at the office",
            "stage3": {"structure": {"effect": "submit the form"}},
            "stage4": {"decision": "Essential"},
        }
    ]

    graph = GraphBuilder.build_graph(particle_data, log_data)

    constraint_edges = [edge for edge in graph.edges if edge.morphism_type == "Constraint"]
    assert constraint_edges == []


def test_stage5_actor_without_explicit_target_does_not_create_constraint_edge():
    particle_data = [
        {"id": "agent-1", "label": "I", "entity_type": "Agent"},
        {"id": "event-1", "label": "submit the form", "entity_type": "Event"},
    ]
    log_data = [
        {
            "input": "I submit the form",
            "stage3": {"structure": {"effect": "submit the form"}},
            "stage5": {"result": "Actor: I"},
        }
    ]

    graph = GraphBuilder.build_graph(particle_data, log_data)

    constraint_edges = [edge for edge in graph.edges if edge.morphism_type == "Constraint"]
    assert constraint_edges == []


def test_stage5_summary_is_an_event_attribute_and_linked_features_remain_nodes():
    particle_data = [
        {"id": "event-1", "label": "I submitted the form", "entity_type": "Effect"},
        {
            "id": "morphology-summary",
            "label": "[Morphology: Base] -> [Category: Action]",
            "entity_type": "Morphology",
            "properties": {"result": "General action statement."},
        },
        {
            "id": "passive-feature",
            "label": "Passive",
            "entity_type": "Morphology",
            "constraints": ["Voice: Passive"],
            "properties": {"event_particle_id": "event-1"},
        },
    ]
    log_data = [
        {
            "stage3": {"structure": {"effect_particle_id": "event-1"}},
            "stage5": {
                "process": "[Morphology: Base] -> [Category: Action]",
                "result": "General action statement.",
            },
        }
    ]

    graph = GraphBuilder.build_graph(particle_data, log_data)

    nodes_by_id = {node.id: node for node in graph.nodes}
    assert "morphology-summary" not in nodes_by_id
    assert nodes_by_id["event-1"].attributes["stage5_result"] == "General action statement."
    assert "passive-feature" in nodes_by_id
    assert any(
        edge.source == "passive-feature"
        and edge.target == "event-1"
        and edge.morphism_type == "Constraint"
        for edge in graph.edges
    )


def test_particle_constraint_uses_explicit_target_particle_id():
    particle_data = [
        {
            "id": "cause-1",
            "label": "missed the train",
            "entity_type": "Cause",
            "target_particle_id": "effect-1",
            "constraints": ["Agent: I + Marker: because"],
        },
        {
            "id": "effect-1",
            "label": "arrived late",
            "entity_type": "Effect",
            "constraints": ["Agent: I + Marker: because"],
        },
    ]

    graph = GraphBuilder.build_graph(particle_data, [])

    constraint_edges = [edge for edge in graph.edges if edge.morphism_type == "Constraint"]
    assert len(constraint_edges) == 1
    assert constraint_edges[0].source == "cause-1"
    assert constraint_edges[0].target == "effect-1"
    assert constraint_edges[0].detail == "Agent: I + Marker: because"


def test_particle_constraint_uses_explicit_event_target():
    particle_data = [
        {
            "id": "temporal-1",
            "label": "the long meeting",
            "entity_type": "Temporal",
            "constraints": ["Agent: I + Temporal Marker: after"],
            "properties": {
                "event": "I was stressed",
                "event_particle_id": "event-1",
            },
        },
        {"id": "event-1", "label": "I was stressed", "entity_type": "Effect"},
    ]

    graph = GraphBuilder.build_graph(particle_data, [])

    constraint_edges = [edge for edge in graph.edges if edge.morphism_type == "Constraint"]
    assert len(constraint_edges) == 1
    assert constraint_edges[0].source == "temporal-1"
    assert constraint_edges[0].target == "event-1"
    assert constraint_edges[0].constraint_type == "TemporalCondition"


def test_cause_edges_disambiguate_duplicate_cause_labels_by_constraints():
    particle_data = [
        {"id": "agent-unknown", "label": "Unknown", "entity_type": "Agent"},
        {
            "id": "cause-unknown",
            "label": "you helped",
            "entity_type": "Cause",
            "constraints": ["Agent: Unknown + Marker: because"],
        },
        {
            "id": "effect-unknown",
            "label": "succeeded",
            "entity_type": "Effect",
            "constraints": ["Agent: Unknown + Marker: because"],
        },
        {"id": "agent-i", "label": "I", "entity_type": "Agent"},
        {
            "id": "cause-i",
            "label": "you helped",
            "entity_type": "Cause",
            "constraints": ["Agent: I + Marker: because"],
        },
        {
            "id": "effect-i",
            "label": "i succeeded",
            "entity_type": "Effect",
            "constraints": ["Agent: I + Marker: because"],
        },
    ]
    log_data = [
        {
            "stage1": {"agent": "Unknown"},
            "stage3": {
                "structure": {
                    "cause": "you helped",
                    "effect": "succeeded",
                    "cause_particle_id": "cause-unknown",
                    "effect_particle_id": "effect-unknown",
                    "agent_particle_id": "agent-unknown",
                }
            },
        },
        {
            "stage1": {"agent": "I"},
            "stage3": {
                "structure": {
                    "cause": "you helped",
                    "effect": "i succeeded",
                    "cause_particle_id": "cause-i",
                    "effect_particle_id": "effect-i",
                    "agent_particle_id": "agent-i",
                }
            },
        },
    ]

    graph = GraphBuilder.build_graph(particle_data, log_data)

    cause_edges = [edge for edge in graph.edges if edge.morphism_type == "Cause"]
    assert {(edge.source, edge.target) for edge in cause_edges} == {
        ("cause-unknown", "effect-unknown"),
        ("cause-i", "effect-i"),
    }
    nodes_by_id = {node.id: node for node in graph.nodes}
    assert nodes_by_id["cause-unknown"].attributes["agent"] == "Unknown"
    assert nodes_by_id["cause-i"].attributes["agent"] == "I"
    action_edges = [edge for edge in graph.edges if edge.morphism_type == "Action"]
    assert {(edge.source, edge.target) for edge in action_edges} == {
        ("agent-unknown", "effect-unknown"),
        ("agent-i", "effect-i"),
    }


def test_cause_edges_resolve_stage3_labels_when_particle_ids_are_missing():
    particle_data = [
        {
            "id": "cause-unknown",
            "label": "you helped",
            "entity_type": "Cause",
            "constraints": ["Agent: Unknown + Marker: because"],
        },
        {
            "id": "cause-i",
            "label": "you helped",
            "entity_type": "Cause",
            "constraints": ["Agent: I + Marker: because"],
        },
        {
            "id": "effect-unknown",
            "label": "succeeded",
            "entity_type": "Effect",
            "constraints": ["Agent: Unknown + Marker: because"],
        },
        {
            "id": "effect-i",
            "label": "i succeeded",
            "entity_type": "Effect",
            "constraints": ["Agent: I + Marker: because"],
        },
    ]
    log_data = [
        {
            "stage1": {"agent": "Unknown"},
            "stage3": {"structure": {"cause": "you helped", "effect": "succeeded"}},
        },
        {
            "stage1": {"agent": "I"},
            "stage3": {"structure": {"cause": "you helped", "effect": "i succeeded"}},
        },
    ]

    graph = GraphBuilder.build_graph(particle_data, log_data)

    cause_edges = [edge for edge in graph.edges if edge.morphism_type == "Cause"]
    assert {(edge.source, edge.target) for edge in cause_edges} == {
        ("cause-unknown", "effect-unknown"),
        ("cause-i", "effect-i"),
    }


def test_invalid_explicit_stage3_particle_id_does_not_fall_back_to_label():
    particle_data = [
        {"id": "cause-1", "label": "missed the train", "entity_type": "Cause"},
        {"id": "effect-1", "label": "arrived late", "entity_type": "Effect"},
    ]
    log_data = [
        {
            "stage3": {
                "structure": {
                    "cause": "missed the train",
                    "effect": "arrived late",
                    "cause_particle_id": "unknown-cause-id",
                }
            }
        }
    ]

    graph = GraphBuilder.build_graph(particle_data, log_data)

    cause_edges = [edge for edge in graph.edges if edge.morphism_type == "Cause"]
    assert cause_edges == []


def test_log_context_is_added_to_referenced_events_not_node_at_same_index():
    particle_data = [
        {"id": "agent-i", "label": "I", "entity_type": "Agent"},
        {"id": "unrelated-event", "label": "unrelated event", "entity_type": "Event"},
        {"id": "agent-unknown", "label": "Unknown", "entity_type": "Agent"},
        {
            "id": "cause-unknown",
            "label": "you helped",
            "entity_type": "Cause",
            "constraints": ["Agent: Unknown + Marker: because"],
        },
        {
            "id": "effect-unknown",
            "label": "succeeded",
            "entity_type": "Effect",
            "constraints": ["Agent: Unknown + Marker: because"],
        },
    ]
    log_data = [
        {},
        {},
        {
            "input": "Succeeded yesterday because you helped.",
            "stage1": {"agent": "Unknown"},
            "stage3": {
                "structure": {
                    "cause": "you helped",
                    "effect": "succeeded",
                    "cause_particle_id": "cause-unknown",
                    "effect_particle_id": "effect-unknown",
                }
            },
        },
    ]

    graph = GraphBuilder.build_graph(particle_data, log_data)

    nodes_by_id = {node.id: node for node in graph.nodes}
    assert nodes_by_id["agent-unknown"].attributes["when"] == "Unspecified"
    assert nodes_by_id["unrelated-event"].attributes["when"] == "Unspecified"
    assert nodes_by_id["cause-unknown"].attributes["when"] == "yesterday"
    assert nodes_by_id["effect-unknown"].attributes["when"] == "yesterday"


def test_action_edge_is_omitted_when_agent_label_is_ambiguous():
    particle_data = [
        {"id": "agent-i-1", "label": "I", "entity_type": "Agent"},
        {"id": "agent-i-2", "label": "I", "entity_type": "Agent"},
        {
            "id": "effect-1",
            "label": "submitted the form",
            "entity_type": "Effect",
            "constraints": ["Agent: I"],
        },
    ]
    log_data = [
        {
            "stage1": {"agent": "I"},
            "stage3": {"structure": {"effect": "submitted the form"}},
        }
    ]

    graph = GraphBuilder.build_graph(particle_data, log_data)

    assert not [edge for edge in graph.edges if edge.morphism_type == "Action"]


def test_stage4_constraint_uses_explicit_particle_ids():
    particle_data = [
        {"id": "source-1", "label": "the report", "entity_type": "Entity"},
        {"id": "target-1", "label": "the report is complete", "entity_type": "Effect"},
    ]
    log_data = [
        {
            "stage4": {
                "decision": "Essential",
                "source_particle_id": "source-1",
                "target_particle_id": "target-1",
            }
        }
    ]

    graph = GraphBuilder.build_graph(particle_data, log_data)

    constraint_edges = [edge for edge in graph.edges if edge.morphism_type == "Constraint"]
    assert len(constraint_edges) == 1
    assert constraint_edges[0].source == "source-1"
    assert constraint_edges[0].target == "target-1"


def test_stage3_labels_without_particle_ids_resolve_unique_particles():
    particle_data = [
        {"id": "agent-1", "label": "I", "entity_type": "Agent"},
        {
            "id": "cause-1",
            "label": "missed the train",
            "entity_type": "Cause",
            "constraints": ["Agent: I + Marker: because"],
        },
        {
            "id": "effect-1",
            "label": "arrived late",
            "entity_type": "Effect",
            "constraints": ["Agent: I + Marker: because"],
        },
    ]
    log_data = [
        {
            "stage1": {"agent": "I"},
            "stage3": {
                "structure": {
                    "cause": "missed the train",
                    "effect": "arrived late",
                }
            },
        }
    ]

    graph = GraphBuilder.build_graph(particle_data, log_data)

    cause_edges = [edge for edge in graph.edges if edge.morphism_type == "Cause"]
    assert len(cause_edges) == 1
    assert cause_edges[0].source == "cause-1"
    assert cause_edges[0].target == "effect-1"


def test_manner_edge_uses_explicit_context_and_event_ids():
    particle_data = [
        {"id": "manner-1", "label": "working hard", "entity_type": "Manner"},
        {"id": "effect-1", "label": "He succeeded", "entity_type": "Effect"},
    ]
    log_data = [
        {
            "stage3": {
                "structure": {
                    "relation": "Manner",
                    "context": "working hard",
                    "event": "He succeeded",
                    "context_particle_id": "manner-1",
                    "event_particle_id": "effect-1",
                }
            }
        }
    ]

    graph = GraphBuilder.build_graph(particle_data, log_data)

    manner_edges = [edge for edge in graph.edges if edge.morphism_type == "Manner"]
    assert len(manner_edges) == 1
    assert manner_edges[0].source == "manner-1"
    assert manner_edges[0].target == "effect-1"


def test_stage5_constraint_uses_explicit_particle_ids():
    particle_data = [
        {"id": "agent-1", "label": "I", "entity_type": "Agent"},
        {"id": "event-1", "label": "was told", "entity_type": "Effect"},
    ]
    log_data = [
        {
            "stage5": {
                "result": "Actor: him / Receiver: I.",
                "source_particle_id": "agent-1",
                "target_particle_id": "event-1",
            }
        }
    ]

    graph = GraphBuilder.build_graph(particle_data, log_data)

    constraint_edges = [edge for edge in graph.edges if edge.morphism_type == "Constraint"]
    assert len(constraint_edges) == 1
    assert constraint_edges[0].source == "agent-1"
    assert constraint_edges[0].target == "event-1"
    assert constraint_edges[0].constraint_type == "PassiveState"

from src.graph import GraphBuilder


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


def test_particle_constraints_connect_shared_cause_effect_pair():
    particle_data = [
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
            "properties": {"event": "I was stressed"},
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
    nodes_by_id = {node.id: node for node in graph.nodes}
    assert nodes_by_id["cause-unknown"].attributes["agent"] == "Unknown"
    assert nodes_by_id["cause-i"].attributes["agent"] == "I"
    action_edges = [edge for edge in graph.edges if edge.morphism_type == "Action"]
    assert {(edge.source, edge.target) for edge in action_edges} == {
        ("agent-unknown", "effect-unknown"),
        ("agent-i", "effect-i"),
    }


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
                "structure": {"cause": "you helped", "effect": "succeeded"}
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

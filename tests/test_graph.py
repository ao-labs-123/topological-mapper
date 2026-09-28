from src.graph import GraphBuilder


def test_constraint_edges_target_related_event_not_self_loop():
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
    assert constraint_edges
    assert all(edge.source != edge.target for edge in constraint_edges)


def test_passive_constraint_edges_are_not_self_loops():
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
    assert constraint_edges
    assert all(edge.source != edge.target for edge in constraint_edges)

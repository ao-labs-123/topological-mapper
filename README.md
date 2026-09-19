# Current Phase: topological-mapper

<img width="960" height="540" alt="image" src="https://github.com/user-attachments/assets/4f05a191-cefe-45bd-8b2b-ca36afca9018" />

## Stage 2 of the Cognitive OS Pipeline
Constructs category-theoretic graph networks [topological_graph.json](https://github.com/ao-labs-123/topological-mapper/blob/main/topological_graph.json) from encapsulated particle objects [data/particles.json](https://github.com/ao-labs-123/topological-mapper/blob/main/data/particles.json).


## Overview

This repository handles the **Topological Mapping** phase of the deterministic Cognitive OS.
It ingests discrete `Particle` objects, maps them into **Entities** or **Events**, and automatically wires category-theoretic morphisms (**Cause**, **Action**, **Relation**, **Constraint**) between them.

### Pipeline Position

```text
(Particle Encapsulation) ──> [ particle.json ] ──> [ Topological Mapping ] ──> [ topological_graph.json ]
```

## Category-Theoretic Mapping Model
The engine structures the cognitive space into two primary object categories connected by functional morphisms

```text
  [ Category of Entities ]                  [ Category of Events ]
  ( Who / Subject / Agent )                 ( What / Cause / Effect )
              │                                         │
              └─────────────── [ Morphisms ] ───────────┘
                       ( Action / Cause / Constraint )
```

### 1. Nodes (Objects)

- **Entity⁠:** Agents, Subjects, and Nouns (`⁠He`⁠, `⁠I⁠`, `⁠you`⁠, etc.)
- **Event⁠:** Actions, Causes, and Contextual Events (`⁠i helped⁠`, `⁠he succeeded⁠`, etc.)

### 2. Edges (Morphism / Wires)

- ⁠**source⁠:** Domain object ID
- ⁠**target⁠:** Codomain object ID
- ⁠**morphism_type⁠:** Functional relation classification (⁠`Cause⁠`, ⁠`Action`⁠, ⁠`Relation⁠`, ⁠`Constraint`⁠)

## Quick Start
### 1. Execution

Ingest ⁠`particle.json⁠` (local or via automated fetch) and generate the topological graph network:

```bash
python -m src.main
```

### 2. Output Example (⁠topological_graph.json⁠)
```topological_graph.json
{
  "nodes": [  
    {
      "id": "p_agent_d27d95",
      "label": "He",
      "category": "Entity"
    },
    {
      "id": "p_effect_fd4b08",
      "label": "he succeeded",
      "category": "Event"
    }
  ],
  "edges": [
    {
      "id": "e_cause_p_cause_90339b_p_effect_fd4b08",
      "source": "p_cause_90339b",
      "target": "p_effect_fd4b08",
      "morphism_type": "Cause"
    }
  ]
}
```


## Repository Structure

```text
topological-mapping/
├── README.md               # Project documentation
├── data/
│   ├── log.json            # Input log data
│   └── particles.json      # Ingested particle objects
├── topological_graph.json  # Exported topological network graph
└── src/
  ├── main.py             # Pipeline execution script
    └── graph.py            # Graph data structures and GraphBuilder logic
```

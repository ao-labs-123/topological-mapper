# Micro—ACT-R (tentative)
> "ACT-R at a Micro-Scale"
## What makes this different from standard ACT-R?

Standard ACT-R operates on a macro level with production rules. This project zooms into the micro-level of cognitive processing.

## Overview
**Micro–ACT-R operates through a clear, fully explainable pipeline from input to reasoning and execution:**

First, text is acquired from the **Environment** and parsed in the **Input** stage into individual cognitive **particles** (Particle Encapsulation).

Next, during **Reasoning**, the system uses **Topological Mapping** to define relationships between particles and assigns explicit spatial coordinates via **Spatial Allocation**. These coordinates are logged directly into **Storage**.

The system then validates consistency between the category of knowledge and past experiences **(Match & Select)**, selects the appropriate action based on this consistency **(Execution)**, and finally produces the **Output**.

## Micro-ACT-R Pipeline Architecture
<img width="960" height="540" alt="image" src="https://github.com/user-attachments/assets/4f05a191-cefe-45bd-8b2b-ca36afca9018" />

1. [input-parser](https://github.com/ao-labs-123/input-parser)
2. [particle-encapsulation](https://github.com/ao-labs-123/particle-encapsulation)
3. [topological-mapper](https://github.com/ao-labs-123/topological-mapper)※Current Position

# Current Phase: topological-mapper
![alt text](image-1.jpeg)

## Stage 2 of the Cognitive OS Pipeline
Constructs category-theoretic graph networks [topological_graph.json](https://github.com/ao-labs-123/topological-mapper/blob/main/topological_graph.json) from encapsulated particle objects [data/particles.json](https://github.com/ao-labs-123/topological-mapper/blob/main/data/particles.json).


## Overview

This repository handles the **Topological Mapping** phase of the deterministic Cognitive OS.
It ingests discrete `Particle` objects, maps them into **Entities** or **Events**, and automatically wires category-theoretic morphisms (**Cause**, **Action**, **Relation**, **Constraint**) between them.

### Pipeline Position

```text
(Particle Encapsulation) ──> [ particle.json ] ──> [ Topological Mapping ] ──> [ topological_graph.json ]
```
## Topology & Graph Design

### 1. Architectural Diagram
```text
  [ Category of Entities ]                  [ Category of Events ]
  ( Who / Subject / Agent )                 ( What / Cause / Effect )
   └── 5W1H: Who                             └── 5W1H: What
              │                                         │
              ├─────────────── [ Morphisms ] ───────────┤
              │        ( Action / Cause / Constraint )  │
              │                                         │
              └───────── [ Context Attributes ] ────────┘
                      ( When / Where / Why / How )

```

### 2. Node & Edge Definitions

#### Nodes (Objects)
* **Entity**: Agents, Subjects, and Nouns (`He`, `I`, `you`, etc.)  
  * *Primary 5W1H Role*: `Who`
* **Event**: Actions, Causes, and Contextual Events (`the project`, `i succeeded`, etc.)  
  * *Primary 5W1H Role*: `What` (and contextual occurrences)

#### Edges (Morphisms / Wires)
* **`source`**: Domain object ID (始点オブジェクト)
* **`target`**: Codomain object ID (終点オブジェクト)
* **`morphism_type`**: Functional relation classification (`Action`, `Cause`, `Constraint`, `Relation`)
* **`attributes` / `detail`**: Contextual bound conditions (`When`, `Where`, `Why`, `How`)

### Explicit Particle References

Edges are created only from particle IDs supplied by the upstream stages. Labels, array positions, and matching constraint text are not used to infer edge endpoints. Missing, unknown, duplicated, or wrong-type references produce no edge.

Stage 3 `structure` may include `agent_particle_id`, `cause_particle_id`, `effect_particle_id`, `context_particle_id`, and `event_particle_id` as applicable. Stage 4/5 may include `source_particle_id` and `target_particle_id`. Particle-level constraints use `target_particle_id` or `properties.event_particle_id`.

Each reference must equal the target particle's existing `id`, for example:

```json
{
  "stage3": {
    "structure": {
      "cause": "you helped",
      "effect": "I succeeded",
      "cause_particle_id": "p_cause_123",
      "effect_particle_id": "p_effect_456",
      "agent_particle_id": "p_agent_789"
    }
  }
}
```


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
      "id": "p_agent_6ed29f",
      "label": "He",
      "category": "Entity",
      "resolution_state": "Determined",
      "attributes": {
        "who": "He",
        "what": "Unspecified",
        "when": "Unspecified",
        "where": "Unspecified",
        "why": "Unspecified",
        "how": "Unspecified"
      }
    },
       {
      "id": "p_cause_5211ee",
      "label": "the project",
      "category": "Event",
      "resolution_state": "Determined",
      "attributes": {
        "who": "Unspecified",
        "what": "the project",
        "when": "Unspecified",
        "where": "Unspecified",
        "why": "Unspecified",
        "how": "Unspecified"
      }
    }
  ],
  "edges": [
    {
      "id": "e_cause_p_cause_5211ee_p_effect_caf9ed",
      "source": "p_cause_5211ee",
      "target": "p_effect_caf9ed",
      "morphism_type": "Cause",
      "detail": "Primary Cause"
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
├── visualize.py
├── index.html
└── src/
  ├── main.py             # Pipeline execution script
  └── graph.py            # Graph data structures and GraphBuilder logic
```

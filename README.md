# Current Phase: topological-mapper

<img width="960" height="540" alt="image" src="https://github.com/user-attachments/assets/4f05a191-cefe-45bd-8b2b-ca36afca9018" />

## Stage 2 of the Cognitive OS Pipeline
Constructs category-theoretic graph networks [topological_graph.json](https://github.com/ao-labs-123/topological-mapper/blob/main/topological_graph.json) from encapsulated particle objects [particles.json](https://github.com/ao-labs-123/topological-mapper/blob/main/particles.json).


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

1. Nodes (Objects)

 ⁠**Entity⁠:** Agents, Subjects, and Nouns (⁠He⁠, ⁠I⁠, ⁠you⁠, etc.)
 ⁠**Event⁠:** Actions, Causes, and Contextual Events (⁠i helped⁠, ⁠he succeeded⁠, etc.)
2. Edges (Morphism / Wires)

 ⁠**source⁠:** Domain object ID
 ⁠**target⁠:** Codomain object ID
 ⁠**morphism_type⁠:** Functional relation classification (⁠Cause⁠, ⁠Action⁠, ⁠Relation⁠, ⁠Constraint⁠)

## Quick Start
1. Execution

Ingest ⁠particle.json⁠ (local or via automated fetch) and generate the topological graph network:
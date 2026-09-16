# Current Phase: topological-mapper

<img width="960" height="540" alt="image" src="https://github.com/user-attachments/assets/4f05a191-cefe-45bd-8b2b-ca36afca9018" />

## Stage 2 of the Cognitive OS Pipeline
Constructs category-theoretic graph networks (`topological_graph.json`) from encapsulated particle objects (`particle.json`).

---

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

<img width="1583" height="1134" alt="image" src="https://github.com/user-attachments/assets/0db76574-fef5-428a-aebb-bc49252954ba" />

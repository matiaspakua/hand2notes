# Evolución de los Requisitos

![Imagen original](../20260529_090913-diagrams.jpg)

## Transcripción

- **50%** cambian / evolucionan.

## Requisitos

1. Van a cambiar.
2. Van a ser mal comprendidos.

## Ingeniería de Requisitos

```mermaid
flowchart LR
    E[Elicitación] --> G((Gestión))
    M[Modelado] --> G
    A[Análisis] --> G
    G --> S[[SRS]]
```

## Requisito

**Concepto + representación**

```mermaid
flowchart LR
    U((Universo del discurso))
    P[Proceso IR]
    S[[SRS]]
    C[Propiedades / clasificación]
    X[Cross-cutting concerns]

    U -->|objetivos, requerimientos, contexto| P
    P -->|Requisito| S
    S --> C
    C --> X
    P -->|Propuesta| U
```

## Nota inferior

- Esquema que permite ver los req cuando hay muchos componentes externos.

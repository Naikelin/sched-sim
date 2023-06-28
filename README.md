# Scheduling simulation using Batsim

En este proyecto se está utilizando Batsim para hacer simulaciones del Scheduler, basado en https://github.com/jankopanski/Burst-Buffer-Scheduling/

## Getting started

Este proyecto utiliza:

- Linux: Se está utilizando Windows con WSL (MacOS en específico no funciona con chip M1+).
- Virtualenv: levanta diferentes versiones de Python. https://virtualenv.pypa.io/en/latest/
- Nix: se utiliza un entorno preparado con Batsim y sus herramientas. https://nixos.org/
- El proyecto BurstBuffers: contiene scripts para la generación de **Workloads** y **Platforms**. https://github.com/jankopanski/Burst-Buffer-Scheduling

### Intro

- Batsim simulator https://batsim.readthedocs.io/en/latest/ https://gitlab.inria.fr/batsim/batsim
- Pybatsim scheduler https://gitlab.inria.fr/batsim/pybatsim
- Robin ???

### Problem

Se aborda el problema en sistemas de gestión de recursos y trabajos, como Slurm, proporcionan un soporte marginal para la programación de trabajos con requisitos de Burst Buffer, en particular ignorando los Burst Buffers al realizar el backfilling (relleno hacia atrás). Los autores investigan el impacto de las reservas de Burst Buffer en la eficiencia general de la programación de trabajos en línea para algoritmos comunes: First-Come-First-Served (FCFS) y Shortest-Job-First (SJF) EASY-backfilling.

La función objetivo del algoritmo de programación propuesto es minimizar la suma de los tiempos de espera de los trabajos ponderados por un exponente. Para una permutación P, WPj denota el tiempo de espera del j-ésimo trabajo en Q según el plan de ejecución creado en base a P. La fórmula es la siguiente:

$\min \sum_{j \in Q} (WP_j)^{\beta}$

Donde β es un parámetro del algoritmo.

Se propone un algoritmo de planificación basado en planes con optimización de recocido simulado, que mejora el tiempo de espera medio en más del 20% y la desaceleración media limitada en un 27% en comparación con el SJF-EASY-backfilling consciente del Burst Buffer.

## Nix enviroment

Correr el ambiente con todo instalado utilizando nix:

``` nix-shell shell.nix```
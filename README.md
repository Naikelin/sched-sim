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

## Nix enviroment

Correr el ambiente con todo instalado utilizando nix:

``` nix-shell shell.nix```
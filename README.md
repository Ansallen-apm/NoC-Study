# NoC Design Space Exploration (DSE) Framework

*[中文版 (Chinese Version) 請點此](README_zh.md)*

## Overview
This project is a comprehensive framework dedicated to Network-on-Chip (NoC) Design Space Exploration (DSE). The primary goal is to evaluate, simulate, and compare various NoC topologies, routing algorithms, and flow control mechanisms to find optimal architectural configurations for specific workloads.

Unlike a simple standalone simulator, this project is structured in multiple layers and phases, starting from theoretical Python-based analysis, advancing to C++ functional modeling, and eventually scaling to Transaction-Level Modeling (TLM) and Register-Transfer Level (RTL) implementations.

## Key Objectives
1. **Theoretical Analysis**: Quickly estimate NoC performance limits (Bisection Bandwidth, Channel Loading, Hot Spots) using mathematical models.
2. **Flexible C-Model Simulation**: Provide a fast, modular C++ simulator that can easily swap different topologies and routing algorithms.
3. **Cross-Verification**: Integrate well-known standalone open-source NoC simulators (like BookSim, Noxim) as submodules to establish baselines and verify the correctness of our models.
4. **Hardware Implementation**: Lay the groundwork for hardware-accurate modeling (TLM/RTL) after architectural parameters are chosen.

## Documentation
To understand the details of the project, please refer to the following documents:

*   [**Architecture (`architecture.md`)**](./architecture.md): Detailed explanation of NoC topologies, routing algorithms, and theoretical formulas.
*   [**Implementation Plan (`implementation.md`)**](./implementation.md): Phased approach and structural planning for developing this DSE framework.
*   [**To-Do List (`todo.md`)**](./todo.md): Actionable tasks and upcoming milestones, including third-party simulator integration.

## Directory Structure
*Currently, the legacy code is present. As the implementation phases progress, the directory will be restructured to isolate topologies, routing algorithms, and implementation levels.*

*   `noc_arch_trace/`: Architecture tools and trace analyzers.
*   `noc_c_model/`: Legacy C++ functional model (Will be refactored).
*   `noc_tlm_model/`: SystemC Transaction Level Modeling.
*   `noc_rtl/`: Verilog implementation.

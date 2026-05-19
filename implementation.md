# Implementation Plan: NoC DSE Framework (片上網路架構探索框架實作計畫)

This document outlines the phased implementation strategy for building the comprehensive Network-on-Chip (NoC) Design Space Exploration (DSE) framework.
(本文檔概述了構建綜合性片上網路 (NoC) 架構探索 (DSE) 框架的分階段實作策略。)

---

## Phase 1: Theoretical Analysis & Modeling (階段 1：理論分析與建模)

**Goal (目標):** Build analytical tools to calculate theoretical limits and establish baselines before writing cycle-accurate simulation code.
(在撰寫週期精確的模擬程式碼之前，建立分析工具以計算理論極限並建立基準線。)

*   **Item 1.1: Python Topology Generator (Python 拓撲產生器)**
    *   *Plan (規劃)*: Write Python scripts to generate graph representations of various topologies (e.g., 2D Mesh, Torus, Ring).
      (撰寫 Python 腳本來生成各種拓撲的圖形表示（例如：2D Mesh、Torus、Ring）。)
*   **Item 1.2: Theoretical Metrics Calculator (理論指標計算機)**
    *   *Plan (規劃)*: Implement mathematical formulas in Python to calculate Bisection Bandwidth, Average Distance, and link capacity bounds for the generated topologies.
      (在 Python 中實作數學公式，以計算生成拓撲的二分頻寬、平均距離和連結容量界限。)
*   **Item 1.3: Routing & Traffic Pattern Analyzer (路由與流量模式分析器)**
    *   *Plan (規劃)*: Given a specific traffic matrix (e.g., uniform random) and a routing algorithm (e.g., XY routing), calculate the theoretical Channel Load and identify Potential Hot Spots.
      (給定特定的流量矩陣（如均勻隨機）和路由演算法（如 XY 路由），計算理論通道負載並識別潛在熱點。)

---

## Phase 2: C++ Functional Simulation Refactoring (階段 2：C++ 功能性模擬重構)

**Goal (目標):** Refactor the legacy C model to be highly modular, supporting the topologies and routing algorithms evaluated in Phase 1.
(重構舊版的 C 模型，使其高度模組化，以支援在階段 1 中評估的拓撲和路由演算法。)

*   **Item 2.1: Directory & Architecture Restructuring (目錄與架構重組)**
    *   *Plan (規劃)*: Separate code into distinct folders based on functionality (e.g., `src/topology/`, `src/routing/`, `src/router/`). Abstract out base classes for Topologies and Routers.
      (根據功能將程式碼分類到不同的資料夾中（例如：`src/topology/`、`src/routing/`、`src/router/`）。抽象出拓撲和路由器的基底類別。)
*   **Item 2.2: Expand Topology Support (擴展拓撲支援)**
    *   *Plan (規劃)*: Implement generic interfaces to easily instantiate Mesh, Torus, and arbitrary graph-based network topologies in C++.
      (實作通用介面，以便在 C++ 中輕鬆實例化 Mesh、Torus 以及任意基於圖形的網路拓撲。)
*   **Item 2.3: Expand Routing Algorithm Support (擴展路由演算法支援)**
    *   *Plan (規劃)*: Add support for Adaptive Routing and source-based routing, alongside the existing deterministic XY routing.
      (除了現有的確定性 XY 路由外，新增對自適應路由和基於來源路由的支援。)
*   **Item 2.4: Statistics Collection (統計數據收集)**
    *   *Plan (規劃)*: Add hooks to track latency, throughput, and link utilization to compare against the theoretical Phase 1 Python results.
      (新增鉤子 (hooks) 以追蹤延遲、吞吐量和連結利用率，以便與階段 1 的 Python 理論結果進行比較。)

---

## Phase 3: Cross-Verification Framework (階段 3：交叉驗證框架)

**Goal (目標):** Integrate mature open-source simulators to validate our models and provide a robust baseline.
(整合相對成熟的開源模擬器來驗證我們的模型並提供穩健的基準線。)

*   **Item 3.1: Submodule Integration (Submodule 整合)** - **[COMPLETED (已完成)]**
    *   *Plan (規劃)*: Add prominent standalone simulators (BookSim, Noxim, ProNoC, Constellation) as Git submodules in a `third_party/` directory.
      (在 `third_party/` 目錄中，將著名的獨立模擬器（BookSim, Noxim, ProNoC, Constellation）新增為 Git submodules。)
*   **Item 3.2: Universal Configuration & Format Adapter (通用配置與格式適配器)**
    *   *Plan (規劃)*: Design a unified `NoC_config.yaml` to serve as the master parameter input for all DSE processes. Create parsing scripts that read this YAML and automatically translate the parameters (e.g., topology, routing, packet size) and standard traffic trace files into the distinct, specific input formats required by the four integrated third-party simulators.
      (設計一個統一的 `NoC_config.yaml` 作為所有 DSE 流程的主參數輸入。建立解析腳本，讀取此 YAML 並自動將參數（如拓撲、路由、封包大小）與標準流量 trace 檔案，轉換為這四個整合的第三方模擬器所需的各別特定輸入格式。)
*   **Item 3.3: Automated Orchestration & Comparison Scripts (自動化調度與比較腳本)**
    *   *Plan (規劃)*: Write wrapper scripts that execute these submodules automatically based on the generated configs. Run simulations on our C++ model and the third-party models simultaneously, then extract, parse, and plot comparison graphs (e.g., Latency vs. Injected Load) to establish baselines.
      (撰寫封裝腳本，根據產生的設定檔自動執行這些子模組。同時在我們的 C++ 模型和第三方模型上執行模擬，然後提取、解析並繪製比較圖表（例如：延遲 vs. 注入負載），以建立基準線。)

---

## Phase 4: Hardware Accurate Implementation (階段 4：硬體精確實作)

**Goal (目標):** Translate the optimal architectures found during DSE into hardware representations.
(將 DSE 期間找到的最佳架構轉化為硬體表示形式。)

*   **Item 4.1: TLM Modeling (TLM 建模)**
    *   *Plan (規劃)*: Develop a SystemC Transaction Level Model for faster, timing-approximate simulation.
      (開發 SystemC 交易層級模型，用於更快、時間近似的模擬。)
*   **Item 4.2: RTL Implementation (RTL 實作)**
    *   *Plan (規劃)*: Write synthesizable Verilog code for the best-performing router architecture, matching cycle-for-cycle with the refined C/TLM models.
      (為效能最佳的路由器架構撰寫可合成的 Verilog 程式碼，使其與改良後的 C/TLM 模型達到週期級的精確匹配。)
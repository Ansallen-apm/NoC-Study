# To-Do List (待辦事項清單)

This document tracks immediate and upcoming tasks for the NoC DSE framework project.
(本文檔追蹤 NoC DSE 框架專案中目前和即將進行的任務。)

## High Priority / Phase 1 (高優先級 / 階段 1)

*   [x] **Create Python Topology Generator**: Write base scripts to construct Mesh and Torus networks as abstract graphs.
        **(建立 Python 拓撲產生器)**：撰寫基礎腳本，將 Mesh 和 Torus 網路建構為抽象圖形。
*   [x] **Implement Analytical Formulas**: Code the calculations for Bisection Bandwidth and Average Hop Count in Python.
        **(實作分析公式)**：在 Python 中撰寫二分頻寬和平均跳數的計算程式。

## Medium Priority / Phase 2 (中優先級 / 階段 2)

*   [ ] **Refactor `noc_c_model`**: Break `Router.cpp/h` and `main.cpp` into modular components (`topology`, `routing`, etc.).
        **(重構 `noc_c_model`)**：將 `Router.cpp/h` 和 `main.cpp` 拆分為模組化元件（如 `topology`、`routing` 等）。
*   [ ] **Add Statistics Tracking**: Implement latency, throughput, and link load monitoring in the C++ model.
        **(新增統計數據追蹤)**：在 C++ 模型中實作延遲、吞吐量和連結負載的監控。

## Cross-Verification Integration (交叉驗證整合)

*   [x] **Integrate Open Source Simulators**: Introduce mature, standalone open-source NoC models as submodules to serve as verification baselines.
        **(整合開源模擬器)**：引入成熟的、獨立的開源 NoC 模型作為 submodules，以作為驗證基準。
        *   *Target 1*: **BookSim** (A widely used, flexible cycle-accurate simulator).
            *(目標 1)*：**BookSim** (一個廣泛使用、高彈性的週期精確模擬器)。
        *   *Target 2*: **Noxim** (A well-known cycle-accurate simulator built on SystemC).
            *(目標 2)*：**Noxim** (一個基於 SystemC 建構的著名週期精確模擬器)。
        *   *Target 3*: **ProNoC** (An EDA tool that facilitates prototyping of NoC-based multi-core systems).
            *(目標 3)*：**ProNoC** (一個促進基於 NoC 的多核心系統原型設計的 EDA 工具)。
        *   *Target 4*: **Constellation** (A Chisel-based NoC generator/simulator).
            *(目標 4)*：**Constellation** (一個基於 Chisel 的 NoC 生成器/模擬器)。
    *Note: Added under `third_party/` directory via `git submodule add`.*
    *(註：已透過 `git submodule add` 將這些新增到 `third_party/` 目錄下。)*

*   [ ] **Design Unified `NoC_config.yaml`**: Define a single YAML configuration file to serve as the master input for all NoC DSE parameters (Topology, Routing, Buffer Size, Traffic Pattern).
        **(設計統一的 `NoC_config.yaml`)**：定義一個單一的 YAML 設定檔，作為所有 NoC DSE 參數（拓撲、路由、緩衝區大小、流量模式）的主輸入。
*   [ ] **Develop Adapter Scripts**: Write translation scripts to parse `NoC_config.yaml` and generate simulator-specific config files for BookSim, Noxim, ProNoC, and Constellation.
        **(開發轉接腳本)**：撰寫轉換腳本以解析 `NoC_config.yaml`，並為 BookSim、Noxim、ProNoC 和 Constellation 產生其專屬的設定檔。
*   [ ] **Develop Automated Execution Runners**: Create wrapper scripts to automatically launch the four standalone submodules using their respectively generated configurations.
        **(開發自動化執行器)**：建立封裝腳本，以使用各自產生的設定檔來自動啟動這四個獨立的 submodule。

## Long Term / Phases 3 & 4 (長期任務 / 階段 3 & 4)

*   [ ] **Develop SystemC TLM Model**: Start creating the architecture using SystemC for faster, high-level modeling.
        **(開發 SystemC TLM 模型)**：開始使用 SystemC 建構架構，以進行更快的高階建模。
*   [ ] **Develop Synthesizable RTL**: Write Verilog modules for the chosen optimal NoC architecture.
        **(開發可合成 RTL)**：為選定的最佳 NoC 架構撰寫 Verilog 模組。

# To-Do List (待辦事項清單)

This document tracks immediate and upcoming tasks for the NoC DSE framework project.
(本文檔追蹤 NoC DSE 框架專案中目前和即將進行的任務。)

## High Priority / Phase 1 (高優先級 / 階段 1)

*   [x] **Create Python Topology Generator**: Write base scripts to construct Mesh and Torus networks as abstract graphs.
        **(建立 Python 拓撲產生器)**：撰寫基礎腳本，將 Mesh 和 Torus 網路建構為抽象圖形。
*   [x] **Implement Analytical Formulas**: Code the calculations for Bisection Bandwidth and Average Hop Count in Python.
        **(實作分析公式)**：在 Python 中撰寫二分頻寬和平均跳數的計算程式。
*   [ ] **Fix Python DSE Topology & Routing Logic**:
        - Add explicit Ring topology generation in `topology.py`.
        - Fix XY routing wrap-around calculation for Torus in `metrics.py` to ensure accurate hot-spot analysis.
        **(修正 Python DSE 拓撲與路由邏輯)**：在 `topology.py` 中補齊 Ring 拓撲；修正 `metrics.py` 中 Torus 的 XY 路由 wrap-around 計算，以確保熱點分析準確。
*   [ ] **Update DSE Main Script Integration**: Make `main.py` parse and utilize `NoC_config.yaml` instead of hardcoding a 4x4 configuration.
        **(更新 DSE 主程式整合)**：讓 `main.py` 讀取並使用 `NoC_config.yaml`，取代寫死的 4x4 配置。

## Medium Priority / Phase 2 (中優先級 / 階段 2)

*   [ ] **Refactor `noc_c_model` Architecture**:
        - Remove hardcoded topology sizes in `Config.h` to allow runtime adjustment and DSE sweeps.
        - Decouple topology and routing logic inside `Router.cpp` (currently tightly coupled to Mesh XY).
        **(重構 `noc_c_model` 架構)**：移除 `Config.h` 中寫死的拓撲大小以支援 runtime 調整與 DSE 掃描；解耦 `Router.cpp` 內嚴重耦合的 Mesh 拓撲與 XY 路由邏輯。
*   [ ] **Fix C Model Synchronization**: Resolve the synchronization bug in `step()` where writing to neighbor buffers happens in the same cycle, leading to inaccurate simulation behaviors.
        **(修正 C 模型同步問題)**：解決 `step()` 中同週期寫入鄰居緩衝區的同步問題，確保模擬行為準確。
*   [ ] **Add Statistics Tracking**: Implement missing latency, throughput, and link load monitoring in the C++ model.
        **(新增統計數據追蹤)**：在 C++ 模型中實作完全缺失的延遲、吞吐量和連結負載監控。

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

*   [x] **Design Unified `NoC_config.yaml`**: Define a single YAML configuration file to serve as the master input for all NoC DSE parameters (Topology, Routing, Buffer Size, Traffic Pattern).
        **(設計統一的 `NoC_config.yaml`)**：定義一個單一的 YAML 設定檔，作為所有 NoC DSE 參數（拓撲、路由、緩衝區大小、流量模式）的主輸入。
*   [x] **Develop Adapter Scripts**: Write translation scripts to parse `NoC_config.yaml` and generate simulator-specific config files for BookSim, Noxim, ProNoC, and Constellation.
        **(開發轉接腳本)**：撰寫轉換腳本以解析 `NoC_config.yaml`，並為 BookSim 產生其專屬的設定檔 (其他模擬器的腳本骨架已建立)。
*   [ ] **Implement Remaining Converters**: Fill in the empty converter skeletons for Noxim, ProNoC, and Constellation.
        **(實作剩餘的轉接器)**：將 Noxim, ProNoC 和 Constellation 的 converter 空骨架實作完成。
*   [x] **Develop Automated Execution Runners**: Create wrapper scripts to automatically launch the standalone submodules using their respectively generated configurations.
        **(開發自動化執行器)**：建立封裝腳本，自動讀取配置執行 BookSim，並繪製 Latency vs. Load 圖表。

## Long Term / Phases 3 & 4 (長期任務 / 階段 3 & 4)

*   [ ] **Refactor SystemC TLM Model (`noc_tlm_model`)**:
        - Remove hardcoded `MESH_WIDTH`.
        - Implement accurate hardware modeling in `b_transport` including Virtual Channels (VCs), Switch Allocator, and pipeline stages.
        - Add missing statistics tracking.
        **(重構 SystemC TLM 模型)**：移除寫死的 `MESH_WIDTH`；在 `b_transport` 中精確建模 VC、Switch Allocator 與 pipeline stages；補齊統計數據輸出。
*   [ ] **Refactor Synthesizable RTL (`noc_rtl`)**:
        - Fix `router.v` to actually implement routing logic instead of hardcoding Port 0 -> East forwarding.
        - Fix `arbiter.v` to implement true Round-Robin instead of static priority.
        - Implement a robust Backpressure mechanism.
        - Create a comprehensive Verilog Testbench.
        **(重構可合成 RTL 模型)**：修正 `router.v` 實作真正的路由邏輯而非寫死轉發；修正 `arbiter.v` 實作真正的 Round-Robin 仲裁；實作背壓 (Backpressure) 機制；建立完整的 Testbench。

## Infrastructure & End-to-End Validation (基礎建設與端到端驗證)

*   [ ] **Unified Configuration Parsing**: Ensure `noc_c_model`, `noc_tlm_model`, and `noc_rtl` testbenches all dynamically parse and initialize from `NoC_config.yaml`.
        **(統一設定檔解析)**：確保各階層模型與 Testbench 皆能動態讀取 `NoC_config.yaml` 進行初始化。
*   [ ] **Unit Testing & CI/CD**: Implement unit tests for Python tools and C++ components. Integrate an automated CI/CD pipeline to build models and run tests on push.
        **(單元測試與 CI/CD)**：為 Python 工具與 C++ 元件撰寫單元測試。整合 CI/CD 流程以自動編譯模型並執行測試。
*   [ ] **End-to-End Golden Verification**: Develop an automated pipeline that injects the same traffic trace into all models (C++, TLM, RTL, BookSim) and explicitly compares cycle-accurate behavior.
        **(端到端黃金驗證)**：建立自動化管線，將相同的流量 trace 注入所有模型中，並精確比對它們的週期級行為是否一致。

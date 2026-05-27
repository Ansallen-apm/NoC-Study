<div align="center">
  <a href="#english-version">🇬🇧 English Version</a> &nbsp;&nbsp;&bull;&nbsp;&nbsp; <a href="#中文版本">🇹🇼 中文版本</a>
</div>

<br>

---

<h1 id="english-version">NoC Design Space Exploration (DSE) Framework</h1>

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
*   `third_party/`: Contains integrated open-source standalone simulators for cross-verification (Currently includes: `booksim`, `noxim`, `pronoc`, `constellation`).
*   `dse_tools/`: Python toolkit for NoC Design Space Exploration.
    *   `core/`: Topology and mathematical metric calculators.
    *   `converters/`: YAML to simulator-specific configuration adapters.
    *   `runners/`: Orchestration scripts for parallel execution and cross-verification.
    *   `generators/`: Scripts to build interactive HTML and Markdown reports.
    *   `config/`: Master YAML configuration files (`NoC_config.yaml`, `verification_sweep.yaml`).
    *   `report/`: Persistent storage for generated plots, JSON data, and interactive dashboards.

<br>

---

<br>

<h1 id="中文版本">片上網路架構探索 (DSE) 框架</h1>

## 專案概述
本專案是一個專門用於片上網路 (NoC) 架構探索 (DSE) 的綜合性框架。主要目標是評估、模擬和比較各種 NoC 拓撲結構、路由演算法和流量控制機制，以為特定的工作負載找到最佳的架構配置。

有別於單純的獨立模擬器，本專案分為多個層次和階段：從基於 Python 的理論分析開始，進展到 C++ 功能性建模，最終擴展到交易層級建模 (TLM) 以及暫存器傳輸層級 (RTL) 實作。

## 核心目標
1. **理論分析**: 使用數學模型快速估算 NoC 效能極限，如二分頻寬、通道負載、熱點等。
2. **彈性的 C 模型模擬**: 提供一個快速、模組化的 C++ 模擬器，可以輕鬆抽換不同的拓撲和路由演算法。
3. **交叉驗證**: 整合知名的獨立開源 NoC 模擬器（如 BookSim、Noxim）作為 submodule，以建立基準並驗證我們模型的正確性。
4. **硬體實作**: 在選定架構參數後，為硬體精確建模 (TLM/RTL) 奠定基礎。

## 相關文件
想了解專案的詳細資訊，請參考以下文件：

*   [**架構設計 (`architecture.md`)**](./architecture.md): 詳細解釋 NoC 拓撲、路由演算法及理論公式。
*   [**實作計畫 (`implementation.md`)**](./implementation.md): 開發此 DSE 框架的階段性方法與架構規劃。
*   [**待辦事項 (`todo.md`)**](./todo.md): 待辦事項和即將到來的里程碑，包含第三方模擬器整合計畫。

## 目錄結構
*目前仍保留舊版程式碼。隨著實作階段的推進，目錄將被重構，以隔離拓撲、路由演算法和不同層級的實作。*

*   `noc_arch_trace/`: 架構工具與 Trace 分析器。
*   `noc_c_model/`: 舊版 C++ 功能性模型（將進行重構）。
*   `noc_tlm_model/`: SystemC 交易層級建模。
*   `noc_rtl/`: Verilog 實作。
*   `third_party/`: 包含用於交叉驗證的獨立開源模擬器（目前包含：`booksim`、`noxim`、`pronoc`、`constellation`）。
*   `dse_tools/`: 用於片上網路架構探索的 Python 工具包。
    *   `core/`: 拓撲產生器與數學指標計算器。
    *   `converters/`: 負責將 YAML 轉接至各個第三方模擬器格式的轉接器。
    *   `runners/`: 負責平行執行模擬與交叉驗證的自動化腳本。
    *   `generators/`: 負責產生互動式 HTML 與 Markdown 報告的腳本。
    *   `config/`: 主設定檔目錄 (`NoC_config.yaml`, `verification_sweep.yaml`)。
    *   `report/`: 用於永久存放產生的圖表、JSON 數據與互動式儀表板。

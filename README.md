<div align="center">
  <a href="#english-version">🇬🇧 English Version</a> &nbsp;&nbsp;&bull;&nbsp;&nbsp; <a href="#中文版本">🇹🇼 中文版本</a>
</div>

<br>

---

<h1 id="english-version">NoC Design Space Exploration (DSE) Framework</h1>

## Overview
This project is a comprehensive framework dedicated to Network-on-Chip (NoC) Design Space Exploration (DSE). The primary goal is to evaluate, simulate, and compare various NoC topologies, routing algorithms, and flow control mechanisms to find optimal architectural configurations for specific workloads.

Unlike a simple standalone simulator, this project is structured in multiple layers, starting from theoretical Python-based analysis, advancing to cross-verification with industry-standard simulators, and eventually scaling to C++ functional modeling, Transaction-Level Modeling (TLM), and RTL implementations.

## Project Phases & Status
The development of this DSE framework is structured into four main phases:

*   **Phase 1: Theoretical Analysis (✅ Mostly Complete)**
    *   Python-based mathematical models to quickly estimate NoC performance limits (Bisection Bandwidth, Channel Loading, Hot Spots, Average Hops).
*   **Phase 2: C++ Functional Simulation Refactoring (✅ Mostly Complete)**
    *   Refactored the legacy C++ model to dynamically load configs using `yaml-cpp`, resolved race conditions with double-buffering, and added robust statistics collection for latency and throughput.
*   **Phase 3: Cross-Verification Framework (✅ Mostly Complete)**
    *   Automated Python orchestration pipeline that translates a unified `NoC_config.yaml` to third-party simulator formats, executes sweeps, and generates interactive HTML5 Canvas dashboards (Heatmaps & Latency Curves) for empirical verification against our theoretical models.
*   **Phase 4: Hardware Implementation (📅 Planned)**
    *   Translating optimal architectures into hardware-accurate SystemC TLM and synthesizable Verilog RTL models.

## Integrated 3rd-Party Simulators
To ensure our theoretical models and eventual hardware implementations are accurate, we integrate several well-known standalone open-source NoC simulators as submodules in the `third_party/` directory for cross-verification:

*   **BookSim 2.0**: The classic, cycle-accurate simulator. It serves as our "Golden Model" for verifying topologies, routing latency, and saturation points.
*   **Noxim**: A SystemC-based simulator, particularly renowned for its "Power/Energy" evaluation capabilities, and support for 3D NoC and WiNoC architectures.
*   **ProNoC**: Features a graphical user interface (GUI) and focuses on generating synthesizable RTL (Verilog/VHDL) code directly, making it ideal for FPGA/ASIC implementations.
*   **Constellation**: A Chisel-based NoC generator that is highly parameterized and widely adopted within the RISC-V ecosystem (e.g., Rocket Chip, Chipyard).

## Documentation
*   [**Architecture (`architecture.md`)**](./architecture.md): Detailed explanation of NoC topologies, routing algorithms, and theoretical formulas.
*   [**Implementation Plan (`implementation.md`)**](./implementation.md): Phased approach and structural planning.
*   [**To-Do List (`todo.md`)**](./todo.md): Actionable tasks and upcoming milestones.

## Directory Structure
*   `noc_arch_trace/`: Architecture tools and trace analyzers.
*   `noc_c_model/`: Refactored C++ functional model with dynamic yaml loading and double-buffering.
*   `noc_tlm_model/`: SystemC Transaction Level Modeling (Phase 4).
*   `noc_rtl/`: Verilog implementation (Phase 4).
*   `third_party/`: Integrated open-source standalone simulators (`booksim`, `noxim`, `pronoc`, `constellation`).
*   `dse_tools/`: Core Python toolkit for NoC Design Space Exploration, orchestration, and HTML/Markdown report generation.

<br>

---

<br>

<h1 id="中文版本">片上網路架構探索 (DSE) 框架</h1>

## 專案概述
本專案是一個專門用於片上網路 (NoC) 架構探索 (DSE) 的綜合性框架。主要目標是評估、模擬和比較各種 NoC 拓撲結構、路由演算法和流量控制機制，以為特定的工作負載找到最佳的架構配置。

有別於單純的獨立模擬器，本專案分為多個層次和階段：從基於 Python 的理論分析開始，進展到與業界標準模擬器的交叉驗證，隨後重構 C++ 功能性建模，最終擴展到交易層級建模 (TLM) 以及暫存器傳輸層級 (RTL) 實作。

## 專案階段與目前狀態 (Project Phases & Status)
本框架的開發分為四個主要階段：

*   **階段 1 (Phase 1): 理論分析與建模 (✅ 幾乎完成)**
    *   使用 Python 建立數學模型，快速估算 NoC 的效能極限（如：二分頻寬、通道負載、熱點預測、平均跳數）。
*   **階段 2 (Phase 2): C++ 功能性模擬重構 (✅ 幾乎完成)**
    *   重構 C++ 模型，整合 `yaml-cpp` 使其可動態讀取配置、實作雙重緩衝 (Double-Buffering) 解決競爭危害，並加入完整的統計數據收集（延遲、吞吐量），以支援自動化掃描與比對。
*   **階段 3 (Phase 3): 交叉驗證整合 (✅ 幾乎完成)**
    *   自動化的 Python 調度管線。將統一的 `NoC_config.yaml` 轉換為第三方模擬器格式，自動執行參數掃描，並產生純 JS (HTML5 Canvas) 的互動式儀表板（包含動態熱點圖與延遲曲線），以經驗數據驗證我們的理論模型。
*   **階段 4 (Phase 4): 硬體精確實作 (📅 規劃中)**
    *   在選定最佳架構參數後，將其轉化為硬體精確的 SystemC TLM 模型與可合成的 Verilog RTL 實作。

## 整合的第三方模擬器 (Integrated 3rd-Party Simulators)
為了確保我們的理論模型和未來的硬體實作正確無誤，我們在 `third_party/` 目錄中整合了多個知名的開源 NoC 模擬器作為交叉驗證的基準：

*   **BookSim 2.0**: 最經典的週期精確 (Cycle-accurate) 模擬器。它是我們驗證拓撲與路由延遲的「黃金基準 (Golden Model)」。
*   **Noxim**: 基於 SystemC 開發，特別擅長於「功耗/能量評估 (Power/Energy)」，並且支援 3D NoC 與無線 NoC (WiNoC) 架構。
*   **ProNoC**: 提供圖形介面 (GUI)，主打能夠直接產生可合成的 RTL 程式碼 (Verilog/VHDL)，非常適合 FPGA/ASIC 的快速實作。
*   **Constellation**: 基於 Chisel 語言的 NoC 產生器，具備高度參數化的特性，在 RISC-V 生態系 (如 Rocket Chip, Chipyard) 中被廣泛使用。

## 相關文件
*   [**架構設計 (`architecture.md`)**](./architecture.md): 詳細解釋 NoC 拓撲、路由演算法及理論公式。
*   [**實作計畫 (`implementation.md`)**](./implementation.md): 開發此 DSE 框架的階段性方法與架構規劃。
*   [**待辦事項 (`todo.md`)**](./todo.md): 待辦事項和即將到來的里程碑，包含尚未完成的模組細節。

## 目錄結構
*   `noc_arch_trace/`: 架構工具與 Trace 分析器。
*   `noc_c_model/`: 重構後的 C++ 功能性模型（支援動態 yaml 讀取與雙重緩衝機制）。
*   `noc_tlm_model/`: SystemC 交易層級建模 (Phase 4)。
*   `noc_rtl/`: Verilog 實作 (Phase 4)。
*   `third_party/`: 包含用於交叉驗證的獨立開源模擬器 (`booksim`, `noxim`, `pronoc`, `constellation`)。
*   `dse_tools/`: 核心 Python 工具包，負責理論計算、模擬器調度、以及 HTML/Markdown 報告的自動生成。

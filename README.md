# NoC Design Space Exploration (DSE) Framework (片上網路架構探索框架)

## Overview (專案概述)
This project is a comprehensive framework dedicated to Network-on-Chip (NoC) Design Space Exploration (DSE). The primary goal is to evaluate, simulate, and compare various NoC topologies, routing algorithms, and flow control mechanisms to find optimal architectural configurations for specific workloads.
(本專案是一個專門用於片上網路 (NoC) 架構探索 (DSE) 的綜合性框架。主要目標是評估、模擬和比較各種 NoC 拓撲結構、路由演算法和流量控制機制，以為特定的工作負載找到最佳的架構配置。)

Unlike a simple standalone simulator, this project is structured in multiple layers and phases, starting from theoretical Python-based analysis, advancing to C++ functional modeling, and eventually scaling to Transaction-Level Modeling (TLM) and Register-Transfer Level (RTL) implementations.
(有別於單純的獨立模擬器，本專案分為多個層次和階段：從基於 Python 的理論分析開始，進展到 C++ 功能性建模，最終擴展到交易層級建模 (TLM) 以及暫存器傳輸層級 (RTL) 實作。)

## Key Objectives (核心目標)
1. **Theoretical Analysis (理論分析)**: Quickly estimate NoC performance limits (Bisection Bandwidth, Channel Loading, Hot Spots) using mathematical models.
   (使用數學模型快速估算 NoC 效能極限，如二分頻寬、通道負載、熱點等。)
2. **Flexible C-Model Simulation (彈性的 C 模型模擬)**: Provide a fast, modular C++ simulator that can easily swap different topologies and routing algorithms.
   (提供一個快速、模組化的 C++ 模擬器，可以輕鬆抽換不同的拓撲和路由演算法。)
3. **Cross-Verification (交叉驗證)**: Integrate well-known standalone open-source NoC simulators (like BookSim, Noxim) as submodules to establish baselines and verify the correctness of our models.
   (整合知名的獨立開源 NoC 模擬器（如 BookSim、Noxim）作為 submodule，以建立基準並驗證我們模型的正確性。)
4. **Hardware Implementation (硬體實作)**: Lay the groundwork for hardware-accurate modeling (TLM/RTL) after architectural parameters are chosen.
   (在選定架構參數後，為硬體精確建模 (TLM/RTL) 奠定基礎。)

## Documentation (相關文件)
To understand the details of the project, please refer to the following documents:
(想了解專案的詳細資訊，請參考以下文件：)

*   [**Architecture (`architecture.md`)**](./architecture.md): Detailed explanation of NoC topologies, routing algorithms, and theoretical formulas. (詳細解釋 NoC 拓撲、路由演算法及理論公式。)
*   [**Implementation Plan (`implementation.md`)**](./implementation.md): Phased approach and structural planning for developing this DSE framework. (開發此 DSE 框架的階段性方法與架構規劃。)
*   [**To-Do List (`todo.md`)**](./todo.md): Actionable tasks and upcoming milestones, including third-party simulator integration. (待辦事項和即將到來的里程碑，包含第三方模擬器整合計畫。)

## Directory Structure (目錄結構)
*Currently, the legacy code is present. As the implementation phases progress, the directory will be restructured to isolate topologies, routing algorithms, and implementation levels.*
*(目前仍保留舊版程式碼。隨著實作階段的推進，目錄將被重構，以隔離拓撲、路由演算法和不同層級的實作。)*

*   `noc_arch_trace/`: Architecture tools and trace analyzers. (架構工具與 Trace 分析器。)
*   `noc_c_model/`: Legacy C++ functional model (Will be refactored). (舊版 C++ 功能性模型，將進行重構。)
*   `noc_tlm_model/`: SystemC Transaction Level Modeling. (SystemC 交易層級建模。)
*   `noc_rtl/`: Verilog implementation. (Verilog 實作。)

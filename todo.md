# 待辦事項清單 (To-Do List)

本文檔追蹤片上網路架構探索 (NoC DSE) 框架專案中目前和即將進行的任務。

## 階段 1：理論分析與建模 (Phase 1)

*   [x] **建立 Python 拓撲產生器**：撰寫基礎腳本，將 Mesh、Torus 與 Ring 網路建構為抽象圖形 (利用 `networkx`)。
*   [x] **實作分析公式**：在 Python 中撰寫二分頻寬 (Bisection BW)、平均跳數 (Avg Hops) 與最大通道負載 (Max Load) 的計算程式。
*   [x] **修正 Python DSE 拓撲與路由邏輯**：補齊 Ring 拓撲；修正 Torus 的 XY 路由邊界環繞 (wrap-around) 計算，以確保熱點分析準確。
*   [x] **更新 DSE 主程式整合**：讓 `main.py` 動態讀取並使用 `NoC_config.yaml` 進行參數化分析，取代寫死的 4x4 配置。

## 階段 2：C++ 模型重構 (Phase 2)

*   [ ] **重構 `noc_c_model` 架構**：移除 `Config.h` 中寫死的拓撲大小以支援 runtime 調整與 DSE 掃描；解耦 `Router.cpp` 內嚴重耦合的 Mesh 拓撲與 XY 路由邏輯。
*   [ ] **修正 C 模型同步問題**：解決 `step()` 中同週期寫入鄰居緩衝區的同步與競爭 (Race Condition) 問題，確保模擬行為準確。
*   [ ] **新增統計數據追蹤**：在 C++ 模型中實作完全缺失的延遲 (Latency)、吞吐量 (Throughput) 和連結負載 (Link Load) 監控。

## 階段 3：交叉驗證整合 (Cross-Verification Integration)

*   [x] **整合開源模擬器**：引入成熟的開源 NoC 模型 (BookSim, Noxim, ProNoC, Constellation) 作為 Git submodules，以作為驗證基準。
*   [x] **設計統一設定檔 `NoC_config.yaml`**：定義單一 YAML 檔作為所有 DSE 參數（拓撲、路由、緩衝區、流量）的主輸入。
*   [x] **開發轉接腳本 (Adapter Scripts)**：撰寫轉換腳本以解析 YAML，並為 BookSim 產生專屬設定檔 (Noxim, ProNoC, Constellation 骨架已建立)。
*   [ ] **實作剩餘轉接器**：將 Noxim, ProNoC 和 Constellation 的轉換器空骨架實作完成。
*   [x] **開發自動化執行器 (Runners)**：建立封裝腳本，自動讀取配置並執行 BookSim。
*   [x] **擴充驗證資料集 (Comprehensive Sweep)**：掃描涵蓋完整注入率 (Injection Rates) 陣列，以完整記錄 Latency 曲線資料。
*   [x] **開發互動式 DSE 報告產生器 (Interactive HTML Report)**：利用 Chart.js 產生可切換拓撲與節點數、並能動態呈現效能趨勢與飽和點的互動式網頁報告。

## 階段 4：硬體精確實作 (Phases 3 & 4)

*   [ ] **重構 SystemC TLM 模型 (`noc_tlm_model`)**：移除寫死的 `MESH_WIDTH`；在 `b_transport` 中精確建模虛擬通道 (VC)、Switch Allocator 與管線級數 (Pipeline stages)；補齊統計數據輸出。
*   [ ] **重構可合成 RTL 模型 (`noc_rtl`)**：修正 `router.v` 實作真正的路由邏輯；修正 `arbiter.v` 實作真正的 Round-Robin 仲裁；實作背壓 (Backpressure) 機制；建立完整的 Testbench。

## 基礎建設與端到端驗證 (Infrastructure)

*   [ ] **統一設定檔解析**：確保 C++, TLM, RTL 各階層模型與 Testbench 皆能動態讀取 `NoC_config.yaml` 進行初始化。
*   [ ] **單元測試與 CI/CD**：為 Python 工具與 C++ 元件撰寫單元測試。整合 GitHub Actions 等 CI/CD 流程以自動編譯模型並執行測試。
*   [ ] **端到端黃金驗證 (End-to-End Golden Verification)**：建立自動化管線，將相同的流量 Trace 注入所有模型中，並精確比對它們的週期級行為是否完全一致。

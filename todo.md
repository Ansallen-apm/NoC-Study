# 待辦事項清單 (To-Do List)

本文檔追蹤片上網路架構探索 (NoC DSE) 框架專案中目前和即將進行的任務。

## 階段 1：理論分析與建模 (Phase 1)

*   [x] **建立 Python 拓撲產生器**：撰寫基礎腳本，將 Mesh、Torus 與 Ring 網路建構為抽象圖形 (利用 `networkx`)。
*   [x] **實作分析公式 (First-Order)**：在 Python 中撰寫二分頻寬 (Bisection BW)、平均跳數 (Avg Hops) 與最大通道負載 (Max Load) 的計算程式。
*   [x] **修正 Python DSE 拓撲與路由邏輯**：補齊 Ring 拓撲；修正 Torus 的 XY 路由邊界環繞 (wrap-around) 計算，以確保熱點分析準確。
*   [x] **更新 DSE 主程式整合**：讓 `main.py` 動態讀取並使用 `NoC_config.yaml` 進行參數化分析，取代寫死的 4x4 配置。

### 階段 1.5：進階微觀分析與二階理論 (Advanced Micro-Metrics Modeling)
*(目的：將尚未與 BookSim 進行深度交叉驗證的微觀指標納入 Python 理論模型)*
*   [x] **精確熱點空間分佈比對 (Spatial Correlation)**：解析 BookSim 的單一通道流量日誌 (`print_activity=1`)，並與 Python 算出的 `theory_edge_loads` 進行 1:1 的相關性比對，確保熱點位置完全一致 (Correlation ~0.999)。
*   [x] **引入排隊理論 (Queueing Theory)**：在 Python 中加入 M/M/1 或 M/D/1 排隊模型，以推算最大延遲 (Max Latency) 與延遲變異數 (Variance)，藉此與 BookSim 的 QoS 數據比對。
*   [x] **非線性延遲曲線擬合 (Curve Fitting)**：使用非線性迴歸分析 BookSim 的延遲攀升曲線，驗證其是否符合排隊理論的 $L = Base + \frac{Queue}{1 - (Rate/Max\_Rate)}$ 數學模型。
*   [x] **緩衝區佔用率建模 (Buffer Occupancy Modeling)**：在 Python 建立馬可夫鏈 (Markov Chain) 模型，預估 Credit 回傳延遲對有限 Buffer 滿載率的影響，並與 BookSim 的 Buffer Stats 進行比對。

## 階段 2：C++ 模型重構 (Phase 2)

*   [x] **重構 `noc_c_model` 架構 (Topology/Routing)**：
    *   [x] 移除 `Config.h` 中寫死的 `MESH_WIDTH` 和 `MESH_HEIGHT`，以支援 runtime 調整與 DSE 參數掃描。
    *   [x] 整合 `yaml-cpp` 使 C++ 模型能與 Python 共用 `NoC_config.yaml`。
    *   [x] 解耦 `Router.cpp` 內嚴重耦合的 Mesh 拓撲與 XY 路由邏輯。
    *   [x] 實作抽象的 Router 介面，以支援不同的拓撲 (Torus, Ring) 和路由演算法。
*   [x] **修正 C 模型同步與架構問題**：
    *   [x] 解決 `step()` 中同週期寫入鄰居緩衝區的同步與競爭 (Race Condition) 問題。
    *   [x] 實作 Pipeline 階段或 Double Buffering 以正確模擬硬體行為。
*   [ ] **新增統計數據追蹤 (Statistics Collection)**：
    *   [x] 在 C++ 模型中實作追蹤每封包的延遲 (Latency)。
    *   [x] 計算整體的吞吐量 (Throughput)。
    *   [ ] 監控與記錄每個連結的使用率 (Link Load)，以利與 Python 理論分析進行交叉驗證。
*   [x] **開發 C++ 自動化掃描與驗證管線 (C++ Benchmarking)**：
    *   [x] 開發 `run_c_model_dse.py` 執行與 BookSim 相同的注入率參數掃描。
    *   [x] 開發 `generate_c_model_report.py` 產生 C++ 理論與 BookSim 的交叉比較分析報告 (`c_model_report.md`)。


## 階段 2.5：Huawei Cycle-Accurate C++ 模型實作 (Phase 2.5)
*(請務必參考 `Huawei_CA_model_plan.md` 進行實作與架構設計，目標為建立 bufferless multi-ring NoC 模擬器)*

### 開發里程碑 (Implementation Phases)
*   [x] **Phase 0 — 模擬器骨架 (Simulator Skeleton)**
    *   [x] 實作 Component base class 與 `tick()` / `tock()` 雙階段週期迴圈。
    *   [x] 實作 YAML 設定檔解析 (`Config`) 與基礎統計元件 (`StatCollector`)。
    *   [x] 建立基礎單元測試框架 (GoogleTest 整合)。
*   [x] **Phase 1 — 單向半環 (Single Half-Ring)**
    *   [x] 實作 Ring slot movement。
    *   [x] 實作 Cross station pass-through。
    *   [x] 實作基礎的 InjectQueue / EjectQueue 與 Latency 量測。
*   [x] **Phase 2 — 雙向全環 (Full-Ring)**
    *   [x] 實作 CW / CCW movement 與 shortest-path 方向選擇。
    *   [x] 實作 per-direction injection arbitration。
*   [x] **Phase 3 — I-Tag / E-Tag 機制**
    *   [x] 實作 I-tag slot injection reservation，避免 starvation。
    *   [x] 實作 E-tag ejection reservation，避免 endless deflection (livelock)。
*   [x] **Phase 4 — RBRG-L1 Multi-Ring**
    *   [x] 實作 Vertical / horizontal ring topology 建立。
    *   [x] 實作 RBRG-L1 佇列與 cross-ring routing (XY / YX routing)。
*   [x] **Phase 5 — RBRG-L2 與 Die-to-Die Link**
    *   [x] 實作 RBRG-L2 queueing, backpressure 與 credit control。
    *   [x] 實作 D2D link latency 與 chiplet-to-chiplet 跨越。
*   [x] **Phase 6 — SWAP 死結恢復 (Deadlock Recovery)**
    *   [x] 實作 Deadlock detector 與 DRM state machine。
    *   [x] 實作 Reserved TX buffer 與 same-cycle eject/inject SWAP 行為。
*   [x] **Phase 7 — Server-CPU 實驗與拓撲**
    *   [x] 定義 Server topology config (CPU clusters, L3, DDRC)。
    *   [x] 執行 empty network latency 與 DDR latency sweep 測試。
*   [x] **Phase 8 — AI-Processor 實驗與拓撲**
    *   [x] 定義 AI vertical/horizontal multi-ring topology。
    *   [x] 執行 Read/write ratio sweep 與 bandwidth probes 測試。

### 階段 2.6：模型驗證與交叉比對 (Validation & Verification)
*(包含 Phase 9 / 10 的功能驗收與效能確認)*
*   [x] **功能驗證 (Functional Validation)**
    *   [x] Round-robin arbitration 沒有餓死 local port。
    *   [x] RBRG-L1 能正確完成 intra-die ring change。
    *   [x] RBRG-L2 能正確完成 inter-die transfer。
    *   [x] 在 Synthetic two-ring deadlock 場景下，SWAP 機制能成功打破死結。
    *   [x] 確認沒有封包重複 (flit duplicated) 且無封包遺失 (flit lost)。
*   [x] **週期精確度驗證 (Cycle-Accuracy Validation)**
    *   [x] 空載延遲 (Empty-network latency) 符合預期 Ring distance。
    *   [x] Bridge 與 D2D 延遲符合設定的 pipeline 週期。
    *   [x] 確保每個 Slot 每週期最多只有一個 Flit，且 SWAP 發生時具備 Atomic update。
*   [x] **效能與極限驗證 (Performance Validation)**
    *   [x] 負載接近飽和 (Saturation) 時，Latency 呈現急遽上升趨勢。
    *   [x] Saturation 下，Ring 利用率 (Utilization) 接近預期上限。
    *   [x] AI bandwidth probes 在各節點顯示分佈均衡。

### 階段 2.7：週期精確度視覺化審查 (Cycle-Accurate Visualizer)
*(目的：提供人工 Review 專用的動態週期播放器，以視覺化驗證跨環與死結情境)*
*   [x] **定義通用 Trace JSON 格式**：設計支援 Topology 與每週期 Link/Buffer 狀態的通用 Trace 架構，供所有模型未來共用。
*   [x] **實作 C++ TraceDumper**：將 `huawei_c_model` 的內部狀態（Slot 佔用、佇列深度）精確輸出為上述 JSON。
*   [x] **設計 3x3 交會擁塞測試情境**：建立 `ca_verify_3x3.yaml`，並在 C++ 刻意製造 RBRG-L1 交會點的排隊擁塞。
*   [x] **開發 HTML 動態播放器 (`generate_ca_visualizer.py`)**：讀取 JSON，利用純 JS/Canvas 開發具備 Play/Pause/Step 功能的視覺化網頁。

### 階段 2.8：極限混沌壓力測試 (Chaos Stress Test)
*(目的：透過高強度隨機流量與長時間模擬，激發所有極端複合狀態，以驗證行為覆蓋率與週期精確度穩健性)*
*   [x] **建立高壓混沌拓撲與流量**：建構多環交會網路，並注入極高頻率的 Uniform Random 流量，搭配極小 Buffer 強迫觸發壅塞。
*   [x] **實作動態不變性斷言 (Runtime Invariants)**：在模擬過程中即時驗證「Flit 守恆定理」與「Slot 互斥佔用」。
*   [x] **實作死結解除與活躍度檢查 (Liveness Check)**：監控網路中是否存在永久卡死的封包，證明 SWAP 與 Deflection 機制在極端複合狀態下依然有效。
*   [ ] **量化邊界案例覆蓋率**：統計並印出 Deflection、E-tag、I-tag 與 SWAP 在測試中的觸發總數，證明行為覆蓋充分。

## 階段 3：交叉驗證整合 (Cross-Verification Integration)

*   [x] **整合開源模擬器**：引入成熟的開源 NoC 模型 (BookSim, Noxim, Constellation) 作為 Git submodules，以作為驗證基準。
*   [x] **設計統一設定檔 `NoC_config.yaml`**：定義單一 YAML 檔作為所有 DSE 參數（拓撲、路由、緩衝區、流量）的主輸入。
*   [x] **開發轉接腳本 (Adapter Scripts)**：撰寫轉換腳本以解析 YAML，並為 BookSim 產生專屬設定檔 (Noxim, Constellation 骨架已建立)。
*   [ ] **實作剩餘的模擬器轉接器 (Converters)**：
    *   [ ] 實作 `NoximConverter` (`dse_tools/converters/other_converters.py`)。
    *   [ ] 實作 `ConstellationConverter` (`dse_tools/converters/other_converters.py`)。
*   [x] **整合 Ratatoskr 模擬器 (3D/PPA)**：
    *   [x] **(1) Submodule 初始化**：將 `jmjos/ratatoskr` 新增至 `third_party/ratatoskr`。
    *   [x] **(2) 編譯環境建置**：確認依賴套件並撰寫腳本編譯 Ratatoskr。
    *   [x] **(3) Converter 開發**：撰寫 `dse_tools/converters/ratatoskr_converter.py`，負責將 `NoC_config.yaml` 轉譯為 Ratatoskr 專用的 XML 或 CLI 引數。
    *   [x] **(4) Runner 開發**：撰寫 `dse_tools/runners/run_ratatoskr_dse.py`，負責啟動模擬、解析效能數據 (Avg Latency, Throughput 等) 並匯出為 JSON。
    *   [x] **(5) 交叉比對驗證 (Review Action)**：執行一個微型參數掃描，將 Ratatoskr 的模擬結果與 Python 理論/BookSim 的數據一起放到 DSE 報告中進行 review 比對。
*   [x] **開發自動化執行器 (Runners)**：建立封裝腳本，自動讀取配置並執行 BookSim。
*   [x] **擴充驗證資料集 (Comprehensive Sweep)**：掃描涵蓋完整注入率 (Injection Rates) 陣列，以完整記錄 Latency 曲線資料。
*   [x] **開發互動式 DSE 報告產生器 (Interactive HTML Report)**：利用 Chart.js 產生可切換拓撲與節點數、並能動態呈現效能趨勢與飽和點的互動式網頁報告。


### 階段 3.5：進階交叉驗證與參數擴充 (Advanced Cross-Verification)
*(目的：擴展交叉驗證的範圍，涵蓋更多真實場景與變數)*
*   [ ] **流量模式 (Traffic Patterns) 的驗證**：
    *   [x] 在 Python 理論模型中實作非均勻流量 (如 Transpose, Bit-complement, Tornado) 的熱點與負載期望值計算 (`dse_tools/core/metrics.py`)。
    *   [x] 使用 BookSim 針對多種標準流量模式進行自動化參數掃描模擬 (`verify_traffic_patterns.py`)，確認理論瓶頸與實際飽和點一致。
    *   [ ] 支援匯入真實應用 Trace，進行理論模型與模擬器的端到端比對。
    *   [ ] **支援客製化流量矩陣 (Custom Traffic Matrix)**：(TDD) 開發與驗證跨引擎 (C Model 與 BookSim 近似) 之 Master/Slave 不均勻機率矩陣，確保節點至節點流量分佈的統計一致性。
    *   [ ] **支援節點獨立注入率 (Per-Node Injection Rate)**：支援透過 YAML 陣列格式為每個節點設定不同的發送頻寬 (BW)，並與 `custom_matrix` 結合使用。
*   [ ] **非確定性路由 (Adaptive Routing) 的驗證**：
    *   [ ] 在 Python 核心中建立自適應路由 (Adaptive Routing) 的理論分析模型，推算多路徑負載平衡對最大通道負載的影響。
    *   [ ] 於 BookSim 啟用自適應路由 (如 Minimal Adaptive)，並將其飽和點與延遲結果與 Python 預測進行交叉比對。
*   [ ] **封包長度與虛擬通道 (VC/Packet Size) 影響驗證**：
    *   [ ] 建立不同封包長度如何影響網路實際飽和點的數學/經驗公式。
    *   [ ] 量化不同 VC 數量與緩衝區深度對排程效率及死結 (Deadlock) 避免的影響，並整合進理論模型。
    *   [ ] 透過 BookSim 自動化掃描多種封包大小與 VC 配置組合，並將模擬結果與理論經驗公式進行迴歸比對。

## 視覺化進階 (Future Visualizations)
*   [x] **動態互動式拓撲熱點圖 (Interactive JS Heatmaps)**：將目前產生的靜態 Topology Heatmap (.png) 升級為純 JavaScript (HTML5 Canvas) 實作的動態視窗，支援滑鼠懸停顯示具體 Edge Load 數值。
*   [x] **Mode A (效能動態曲線) UI 改善**：加入「保存曲線/鎖定對比」功能，將舊曲線半透明化，並重構下拉選單分類。
*   [x] **Mode B (架構交叉比對) UI 改善**：加入過濾器 (Filters) 讓使用者自由篩選資料點，並加入 Tooltip 顯示每個點的具體架構配置。
*   [x] **Mode C (通道負載分佈) 擴充**：結合路由演算法的流量動畫或實際 Buffer Occupancy 呈現。
*   [x] **實作 Mode D (架構成本與效能權衡 / Pareto Plot)**：
    *   計算綜合成本（Nodes、Channels、Buffers），並支援使用者動態調整各項目的權重 (Weights)。
    *   X 軸顯示相對於最小 Base 的正規化成本，Y 軸顯示吞吐量或飽和點，繪製柏拉圖前沿 (Pareto Frontier)。
*   [x] **實作 Mode E (極限壓力測試雷達圖 / Radar Chart)**：
    *   顯示五個核心指標（Hops, Max Load, Zero-Load Latency, Saturation Rate, Throughput），並標示「越高越好」或「越低越好」。
    *   支援同時選擇 3 個不同拓撲架構進行雷達圖疊加比對。

## 階段 4：硬體精確實作 (Phases 3 & 4)

*   [ ] **重構 SystemC TLM 模型 (`noc_tlm_model`)**：移除寫死的 `MESH_WIDTH`；在 `b_transport` 中精確建模虛擬通道 (VC)、Switch Allocator 與管線級數 (Pipeline stages)；補齊統計數據輸出。
*   [ ] **重構可合成 RTL 模型 (`noc_rtl`)**：修正 `router.v` 實作真正的路由邏輯；修正 `arbiter.v` 實作真正的 Round-Robin 仲裁；實作背壓 (Backpressure) 機制；建立完整的 Testbench。

## 基礎建設與端到端驗證 (Infrastructure)

*   [x] **專案目錄結構大掃除 (Directory Housekeeping)**：將 `dse_tools/` 內的龐雜腳本分類至 `core/`, `runners/`, `generators/`, `converters/`, `config/` 與 `examples/`，並更新所有相對路徑與 README 文件。
*   [x] **統整 Report 報告模組與路徑重構 (Report System Refactoring)**：
    *   [x] **報告產生模組化**：將 `dse_tools/generators/` 下零散的 HTML 與圖表 (Chart.js) 產生邏輯，抽離成固定的 function/library，並放置於 `scripts/html_gen/` (或命名為 `scripts/report_lib/`) 以供各腳本重複呼叫。
    *   [x] **收斂 Report 目錄與階層標準化**：
        *   將根目錄舊的 `report/` 與 `reports/` 合併，統一保留唯一的 `reports/` 作為根目錄。
        *   實作專案制子資料夾結構：`reports/<專案項目名稱>/`，並在每個專案下標準化切分 `data/` (放 json), `docs/` (放 md), `html/` (放 html)，以及該專案層級的 `index.html`。
        *   預計分類之專案資料夾範例：`reports/cmn_dse/`, `reports/custom_workload/`, `reports/unified_dashboard/`, `reports/cross_verification/` 等。
    *   [x] **腳本路徑更新**：配合上述結構變更，需同步修改以下腳本中寫死的輸出入路徑與 import 來源：
        *   Generator 腳本 (需更新檔案輸出至 `reports/<專案>/...`)：`dse_tools/generators/generate_c_model_report.py`, `generate_custom_workload_html.py`, `generate_html_report.py`, `generate_multi_model_cmp.py`, `generate_unified_dashboard.py`, `generate_verify_table.py` 等。
        *   Runner 腳本 (需更新 json 輸出位置)：`dse_tools/runners/run_c_model_dse.py`, `run_booksim_dse.py`, `verify_cross_correlation.py` 以及 `scripts/` 下的 runner 等。
*   [ ] **統一設定檔解析**：確保 C++, TLM, RTL 各階層模型與 Testbench 皆能動態讀取 `NoC_config.yaml` 進行初始化。
*   [ ] **單元測試與 CI/CD**：為 Python 工具與 C++ 元件撰寫單元測試。整合 GitHub Actions 等 CI/CD 流程以自動編譯模型並執行測試。
*   [ ] **端到端黃金驗證 (End-to-End Golden Verification)**：建立自動化管線，將相同的流量 Trace 注入所有模型中，並精確比對它們的週期級行為是否完全一致。

## 階段 5：統一綜合報告平台 (Unified HTML Dashboard)
*(目的：將散落的各階段報告整合為一個專業、多頁籤的視覺化儀表板)*
*   [x] **整合框架設計**：建立一個基於 HTML/CSS/JS 的 SPA (Single Page Application) 或多頁籤結構，作為所有報告的統一入口。
*   [x] **頁籤 1：巨觀設計空間探索 (Macro DSE)**：將目前的 `interactive_dse_trends.html` 納入，提供 5 種模式 (Latency Curves, Scatter, Channel Load Bar, Pareto, Radar) 的互動式查詢。
*   [x] **頁籤 2：微觀排隊與緩衝區理論 (Micro [ ] **頁籤 2：微觀排隊與緩衝區理論 (Micro & Queueing Theory)** Queueing Theory)**：納入 Phase 1.5 的 `advanced_micro_metrics_report.html`，展示非線性曲線擬合、M/D/1 預測對比、以及 Buffer Occupancy / Congestion Collapse 分析。
*   [x] **頁籤 3：跨引擎交叉驗證 (Cross-Engine Verification)**：將 `verification_summary.md` 轉為動態可排序的資料表 (DataTables)，對齊展示 Python 理論、BookSim、以及 Ratatoskr 等引擎的 bisection BW 與 saturation rate 誤差。
*   [x] **頁籤 4：C++ 模型精準度分析 (C-Model Evaluation)**：將 Phase 2 的 `c_model_report.md` 視覺化，疊加對比 C++ 模型的吞吐量/延遲曲線與 BookSim 基準，並視覺化 Pipeline/Double-Buffering 的影響。
*   [x] **一鍵產出自動化**：開發一個總匯腳本 (如 `make_full_dashboard.py`)，自動抓取 `report/` 目錄下的所有 JSON 產出最終的 `Unified_NoC_Dashboard.html`。

## 階段 6：多模型互動比較分析儀表板 (Multi-Model Comparison Dashboard)
*(目的：開發 `multi_model_cmp.html`，讓使用者能針對單一配置，在同一視圖內疊加比對所有支援之模擬器與模型的 DSE 結果)*
*   [x] **資料源標準化與整併 (Data Aggregation [ ] **資料源標準化與整併 (Data Aggregation & Normalization)** Normalization)**：撰寫資料處理腳本，將 `verification_results.json` (BookSim & Theory)、`c_model_sweep_results.json` (C-Model)、`micro_metrics_results.json` 等離散的資料來源，依據 `(Topology, Dim, Traffic, Routing, VCs)` 作為 Key 進行關聯式合併。
*   [x] **動態過濾器設計 (Dynamic Filters)**：在網頁前端建立全域的選擇器，包含 Topology (Mesh, Torus, Ring)、Dimension (網路大小)、Traffic Pattern (Uniform, Transpose 等) 及 Routing Algorithm。
*   [x] **視覺化疊加圖表 (Overlay Charts)**：
    *   **Latency vs. Injection Rate 曲線圖**：在同一張 Chart.js 圖表中繪製不同引擎的延遲曲線。例如：同時顯示 BookSim (實線)、C-Model (虛線)、Python M/D/1 預估 (點線)，直觀看出各模型的準確度落差。
    *   **Throughput vs. Injection Rate 曲線圖**：對比不同模型在飽和點後的吞吐量衰減或穩定情況。
*   [x] **誤差分析表格 (Error Analysis Table)**：針對選定配置，顯示各個模型在零負載延遲 (Zero-load Latency) 與極限吞吐量 (Saturation Rate) 相對於黃金模型 (BookSim) 的誤差百分比 (%)。
*   [x] **產生器開發**：撰寫 `dse_tools/generators/generate_multi_model_cmp.py`，自動從 `reports/` 抓取資料並生成 `reports/multi_model_cmp.html` 網頁。

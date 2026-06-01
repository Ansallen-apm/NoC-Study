# 待辦事項清單 (To-Do List)

本文檔追蹤片上網路架構探索 (NoC DSE) 框架專案中目前和即將進行的任務。

## 階段 1：理論分析與建模 (Phase 1)

*   [x] **建立 Python 拓撲產生器**：撰寫基礎腳本，將 Mesh、Torus 與 Ring 網路建構為抽象圖形 (利用 `networkx`)。
*   [x] **實作分析公式 (First-Order)**：在 Python 中撰寫二分頻寬 (Bisection BW)、平均跳數 (Avg Hops) 與最大通道負載 (Max Load) 的計算程式。
*   [x] **修正 Python DSE 拓撲與路由邏輯**：補齊 Ring 拓撲；修正 Torus 的 XY 路由邊界環繞 (wrap-around) 計算，以確保熱點分析準確。
*   [x] **更新 DSE 主程式整合**：讓 `main.py` 動態讀取並使用 `NoC_config.yaml` 進行參數化分析，取代寫死的 4x4 配置。

### 階段 1.5：進階微觀分析與二階理論 (Advanced Micro-Metrics Modeling)
*(目的：將尚未與 BookSim 進行深度交叉驗證的微觀指標納入 Python 理論模型)*
*   [ ] **精確熱點空間分佈比對 (Spatial Correlation)**：解析 BookSim 的單一通道流量日誌，並與 Python 算出的 `theory_edge_loads` 進行 1:1 的相關性比對，確保熱點位置完全一致。
*   [ ] **引入排隊理論 (Queueing Theory)**：在 Python 中加入 M/M/1 或 M/D/1 排隊模型，以推算最大延遲 (Max Latency) 與延遲變異數 (Variance)，藉此與 BookSim 的 QoS 數據比對。
*   [ ] **非線性延遲曲線擬合 (Curve Fitting)**：使用非線性迴歸分析 BookSim 的延遲攀升曲線，驗證其是否符合排隊理論的 $L = Base + \frac{Queue}{1 - (Rate/Max\_Rate)}$ 數學模型。
*   [ ] **緩衝區佔用率建模 (Buffer Occupancy Modeling)**：在 Python 建立馬可夫鏈 (Markov Chain) 模型，預估 Credit 回傳延遲對有限 Buffer 滿載率的影響，並與 BookSim 的 Buffer Stats 進行比對。

## 階段 2：C++ 模型重構 (Phase 2)

*   [ ] **重構 `noc_c_model` 架構 (Topology/Routing)**：
    *   移除 `Config.h` 中寫死的 `MESH_WIDTH` 和 `MESH_HEIGHT`，以支援 runtime 調整與 DSE 參數掃描。
    *   解耦 `Router.cpp` 內嚴重耦合的 Mesh 拓撲與 XY 路由邏輯。
    *   實作抽象的 Router 介面，以支援不同的拓撲 (Torus, Ring) 和路由演算法。
*   [ ] **修正 C 模型同步與架構問題**：
    *   解決 `step()` 中同週期寫入鄰居緩衝區的同步與競爭 (Race Condition) 問題。
    *   實作 Pipeline 階段或 Double Buffering 以正確模擬硬體行為。
*   [ ] **新增統計數據追蹤 (Statistics Collection)**：
    *   在 C++ 模型中實作追蹤每封包的延遲 (Latency)。
    *   計算整體的吞吐量 (Throughput)。
    *   監控與記錄每個連結的使用率 (Link Load)，以利與 Python 理論分析進行交叉驗證。

## 階段 3：交叉驗證整合 (Cross-Verification Integration)

*   [x] **整合開源模擬器**：引入成熟的開源 NoC 模型 (BookSim, Noxim, ProNoC, Constellation) 作為 Git submodules，以作為驗證基準。
*   [x] **設計統一設定檔 `NoC_config.yaml`**：定義單一 YAML 檔作為所有 DSE 參數（拓撲、路由、緩衝區、流量）的主輸入。
*   [x] **開發轉接腳本 (Adapter Scripts)**：撰寫轉換腳本以解析 YAML，並為 BookSim 產生專屬設定檔 (Noxim, ProNoC, Constellation 骨架已建立)。
*   [ ] **實作剩餘的模擬器轉接器 (Converters)**：
    *   [ ] 實作 `NoximConverter` (`dse_tools/converters/other_converters.py`)。
    *   [ ] 實作 `PronocConverter` (`dse_tools/converters/other_converters.py`)。
    *   [ ] 實作 `ConstellationConverter` (`dse_tools/converters/other_converters.py`)。
*   [x] **開發自動化執行器 (Runners)**：建立封裝腳本，自動讀取配置並執行 BookSim。
*   [x] **擴充驗證資料集 (Comprehensive Sweep)**：掃描涵蓋完整注入率 (Injection Rates) 陣列，以完整記錄 Latency 曲線資料。
*   [x] **開發互動式 DSE 報告產生器 (Interactive HTML Report)**：利用 Chart.js 產生可切換拓撲與節點數、並能動態呈現效能趨勢與飽和點的互動式網頁報告。


### 階段 3.5：進階交叉驗證與參數擴充 (Advanced Cross-Verification)
*(目的：擴展交叉驗證的範圍，涵蓋更多真實場景與變數)*
*   [ ] **流量模式 (Traffic Patterns) 的驗證**：
    *   [ ] 在 Python 理論模型中實作非均勻流量 (如 Transpose, Bit-complement, Tornado, Hotspot) 的熱點與負載計算。
    *   [ ] 使用 BookSim 針對多種標準流量模式進行模擬，確認理論熱點分佈與實際瓶頸一致。
    *   [ ] 支援匯入真實應用 Trace，進行理論模型與模擬器的端到端比對。
*   [ ] **非確定性路由 (Adaptive Routing) 的驗證**：
    *   [ ] 在 Python 核心中建立自適應路由 (Adaptive Routing) 的理論分析模型，推算多路徑負載平衡對最大通道負載的影響。
    *   [ ] 於 BookSim 啟用自適應路由 (如 Minimal Adaptive)，並將其飽和點與延遲結果與 Python 預測進行交叉比對。
*   [ ] **封包長度與虛擬通道 (VC/Packet Size) 影響驗證**：
    *   [ ] 建立不同封包長度如何影響網路實際飽和點的數學/經驗公式。
    *   [ ] 量化不同 VC 數量與緩衝區深度對排程效率及死結 (Deadlock) 避免的影響，並整合進理論模型。
    *   [ ] 透過 BookSim 自動化掃描多種封包大小與 VC 配置組合，並將模擬結果與理論經驗公式進行迴歸比對。

## 視覺化進階 (Future Visualizations)
*   [x] **動態互動式拓撲熱點圖 (Interactive JS Heatmaps)**：將目前產生的靜態 Topology Heatmap (.png) 升級為純 JavaScript (HTML5 Canvas) 實作的動態視窗，支援滑鼠懸停顯示具體 Edge Load 數值。

## 階段 4：硬體精確實作 (Phases 3 & 4)

*   [ ] **重構 SystemC TLM 模型 (`noc_tlm_model`)**：移除寫死的 `MESH_WIDTH`；在 `b_transport` 中精確建模虛擬通道 (VC)、Switch Allocator 與管線級數 (Pipeline stages)；補齊統計數據輸出。
*   [ ] **重構可合成 RTL 模型 (`noc_rtl`)**：修正 `router.v` 實作真正的路由邏輯；修正 `arbiter.v` 實作真正的 Round-Robin 仲裁；實作背壓 (Backpressure) 機制；建立完整的 Testbench。

## 基礎建設與端到端驗證 (Infrastructure)

*   [x] **專案目錄結構大掃除 (Directory Housekeeping)**：將 `dse_tools/` 內的龐雜腳本分類至 `core/`, `runners/`, `generators/`, `converters/`, `config/` 與 `examples/`，並更新所有相對路徑與 README 文件。
*   [ ] **統一設定檔解析**：確保 C++, TLM, RTL 各階層模型與 Testbench 皆能動態讀取 `NoC_config.yaml` 進行初始化。
*   [ ] **單元測試與 CI/CD**：為 Python 工具與 C++ 元件撰寫單元測試。整合 GitHub Actions 等 CI/CD 流程以自動編譯模型並執行測試。
*   [ ] **端到端黃金驗證 (End-to-End Golden Verification)**：建立自動化管線，將相同的流量 Trace 注入所有模型中，並精確比對它們的週期級行為是否完全一致。

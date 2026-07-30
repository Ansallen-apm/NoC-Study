# Huawei Cycle-Accurate C++ NoC Model

本目錄 (`huawei_c_model`) 包含了一個基於 `Huawei_CA_model_plan.md` 規範所開發的**週期精確 (Cycle-Accurate) 無緩衝區多環 (Bufferless Multi-Ring) 片上網路模擬器**。該模型以 C++17 實作，專為探索異質 Chiplet 架構 (如 Server-CPU 與 AI-Processor) 的通訊行為所設計。

---

## 🌟 核心特色與微架構 (Key Features)

本模型精準模擬了無緩衝區網路在極端負載下的物理與硬體行為：

1. **雙向環狀拓撲 (Bidirectional Ring)**
   - 支援單向半環 (Half-Ring) 與雙向全環 (Full-Ring)。
   - 支援基於最短路徑 (Shortest-path) 的方向選擇機制。

2. **跨站與偏折路由 (CrossStation & Deflection Routing)**
   - 實作無緩衝區網路的核心：當節點的 `EjectQueue` 滿載時，到達的封包 (Flit) 無法順利離開網路，將會被迫留在環上繼續繞圈 (Deflection/Pass-through)。
   - 支援 I-Tag 與 E-Tag 機制以防止餓死 (Starvation) 與活結 (Livelock)。

3. **同晶片 / 跨晶片橋接器 (RBRG-L1 & RBRG-L2)**
   - **RBRG-L1 (Intra-Die)**：負責同一個 Die 內部，垂直環與水平環 (Vertical/Horizontal Rings) 的交會與路由轉發。
   - **RBRG-L2 (Inter-Die)**：負責跨 Die / Chiplet 的通訊，內部實作了可設定延遲的 Die-to-Die (D2D) 管線，並搭載基於 Credit 的流量控制 (Credit-based Flow Control) 來處理背壓 (Backpressure)。

4. **SWAP 死結恢復機制 (Deadlock Recovery)**
   - 當網路發生嚴重擁塞導致封包持續無法注入時，`CrossStation` 會觸發 DRM (Deadlock Resolution Mode) 狀態機。
   - 透過實作 `SwapSink` 介面，在同一個週期內將 `EjectQueue` 內最舊的封包強制移入備用緩衝區 (Reserved TX Buffer)，讓環上的封包得以 Eject，並讓 Local 的封包得以 Inject，以原子操作 (Atomic) 打破死結。

---

## 🛠️ 編譯與執行指南 (Build & Run)

本專案使用 CMake 與 GoogleTest。編譯時會自動抓取 `yaml-cpp` 依賴。

### 編譯模型
```bash
cd huawei_c_model
mkdir -p build && cd build
cmake ..
make -j$(nproc)
```

### 執行內建實驗 (Experiments)
我們提供兩種預先定義的拓撲與實驗場景：
```bash
# 執行 Server-CPU 實驗 (測量 DDR Latency Sweep)
./nocsim --experiment server --config ../configs/server_cpu.yaml

# 執行 AI-Processor 實驗 (測量 Read/Write Ratio Bandwidth Sweep)
./nocsim --experiment ai --config ../configs/ai_processor.yaml
```
> 執行後，實驗數據將會以 CSV 格式輸出至專案根目錄的 `reports/huawei_c_model/` 資料夾下。

---

## 🎥 週期精確度視覺化審查 (Cycle-Accurate Visualizer)

為了讓開發者能以人工方式直觀地驗證跨環路由與背壓現象，我們提供了一個基於 HTML5 Canvas 的動態播放器。

### 1. 產生 Trace 資料
執行特製的 `ca_verify` 擁塞劇本，這會在 3x3 網路中刻意製造碰撞，並輸出 JSON 追蹤日誌：
```bash
cd huawei_c_model/build
./nocsim --experiment ca_verify --config ../configs/ca_verify_3x3.yaml
```
> 這將產生 `reports/huawei_c_model/data/ca_trace.json`。

### 2. 生成 HTML 播放器
回到專案根目錄，執行 Python 腳本將 JSON 轉為視覺化網頁：
```bash
python3 scripts/html_gen/generate_ca_visualizer.py
```

### 3. 觀看與驗證
除了使用瀏覽器打開產生的 `reports/huawei_c_model/html/ca_visualizer.html` 之外，本專案還提供了以下相關的靜態文件來幫助驗證與理解：
- **`huawei_c_model/architecture.html`**：架構設計文件。
- **`huawei_c_model/ca_verify_trace_viewer.html`**：新的 cycle-by-cycle 敘述式 trace viewer，含逐階段的預期行為說明與已知限制警告。

在動態播放器中，您可以透過 **Play/Pause** 或拖曳 **進度條**，觀察：
- Flit 在節點間的移動。
- 游標懸停 (Hover) 在橘色的 Bridge 節點上，可觀看其內部 Ingress/Egress 管線與 Queue 的即時變化。
- 觀察 Bufferless 網路在交會處壅塞時，封包如何發生 Deflection 並持續繞圈。

---

## 🧪 測試與極限驗證 (Testing & Validation)

所有核心元件皆以 TDD (測試驅動開發) 方式撰寫。請透過以下指令執行單元測試：
```bash
cd huawei_c_model/build
./run_tests
```

**重點測試涵蓋：**
- `Phase1Test ~ Phase6Test`：針對半環、全環、I-tag/E-tag 預留、RBRG-L1/L2 以及 SWAP 機制的獨立功能驗證。
- `ConfigTest.*`：驗證 YAML 解析正確性，以及當缺少必要的拓撲/節點欄位時的快速失敗 (fail-fast) 機制。
- `ChaosStressTest.FlitConservationAndLiveness`：高負載下的壓力測試，驗證嚴格的封包守恆 (注入 == 彈出 + 飛行中 + 佇列中)；此測試最初抓出了 RBRG 重複彈出的錯誤。
- `EjectQueueFuzzTest.FuzzCapacityInvariant`：模糊測試，驗證無論 reserve/push 呼叫如何交錯，EjectQueue 的物理大小永遠不會超過容量限制；防範先前發現的 can_reserve()/push() 容量退化問題。
- `ValidationTest.RoundRobinFairness`：驗證站點的多個輸入埠獲得公平的輪詢 (round-robin) 注入仲裁。
- `ValidationTest.FlitConservation`：驗證封包在傳輸過程中沒有發生遺失或意外複製。

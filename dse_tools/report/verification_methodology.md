# NoC DSE 參數驗證方法論 (Verification Methodology)

本文件詳細記錄了片上網路架構探索 (NoC DSE) 框架中，各項關鍵效能指標在三個層次（數學理論、Python 腳本實作、BookSim 硬體模擬）的驗證方式與對應關係。我們的目標是確保理論分析與週期精確模擬的結果能互相印證，從而保證 DSE 結果的正確性。

---

## 1. 核心效能參數與驗證層次對應表

以下表格總結了現有 DSE 框架中，每個效能參數在不同層次的定義與對應關係：

| 效能評估維度 (Dimension) | 1. 理論層次 (Mathematical Theory) | 2. Python 實作 (dse_tools/core) | 3. BookSim 模擬層次 (Cycle-Accurate) | 預期關聯性 (Expected Correlation) |
| :--- | :--- | :--- | :--- | :--- |
| **網路基本延遲 (Base Latency)** | 理論平均跳數<br>(Theoretical Average Hops) | 使用 `networkx.shortest_path_length` 計算均勻流量下所有節點對的平均距離。 | 零負載延遲<br>(Zero-Load Latency) | **完美正相關 (高度線性)。**<br>當注入率趨近於 0 時，排隊延遲為 0，封包只受到純粹的 Router/Link pipeline 延遲影響。 |
| **網路飽和與瓶頸 (Saturation & Bottleneck)** | 理論最大通道負載<br>(Theoretical Max Channel Load) | 給定路由演算法，計算所有路徑中被經過最多次的邊 (Edge)。最大負載的倒數即為理論最大注入率。 | 實際飽和注入率<br>(Actual Saturation Rate) | **高度正相關。**<br>理論最大負載決定了網路哪個節點會先塞爆。BookSim 跑出來的實際飽和點通常會略早於理論值 (因硬體 Allocator 效率並非 100%)。 |
| **全網極限吞吐量 (Total Throughput)** | 理論二分頻寬<br>(Theoretical Bisection Bandwidth) | 計算將圖形切兩半所需的最小割集邊數 (Minimum Edge Cut)。 | 總吞吐量<br>(Total Throughput) | **高度正相關。**<br>即使是 Uniform 流量，當網路全面飽和時，跨越網路中心的總資料量會受到 Bisection BW 的物理限制。 |

---

## 2. 各參數的完整驗證方式拆解

### 2.1 基礎延遲驗證 (Base Latency Verification)

*   **理論與物理意義**：
    *   在沒有任何網路擁塞 (Congestion) 的完美情況下，一個封包從來源走到目的地的時間，取決於它「必須經過幾個路由器」。在均勻隨機 (Uniform Random) 流量下，這個期望值就是「平均跳數 (Average Hops)」。
*   **Python (`dse_tools/core/metrics.py`) 實作**：
    *   **方法**：使用 `networkx` 建立抽象拓撲圖。
    *   **計算**：呼叫 `nx.shortest_path_length(G)` 取得所有節點對的最短距離，然後除以總路徑數。
    *   *註：這假設了 Deterministic shortest-path routing。*
*   **BookSim 驗證方式**：
    *   **設定**：在 `NoC_config.yaml` 中設定極低的 `injection_rate` (例如 `0.01`)。
    *   **觀察指標**：觀察 BookSim 輸出日誌中的 `Packet latency average`。
    *   **比對邏輯**：將這個「零負載延遲」數值繪製在散佈圖的 Y 軸，X 軸放 Python 算出的「平均跳數」。兩者必須呈現斜率為正的完美直線。如果偏離直線，代表該拓撲的路由演算法在 BookSim 中走了非最佳路徑 (Non-minimal path) 或者是繞路 (Wrap-around) 邏輯設定錯誤。

### 2.2 網路飽和點驗證 (Saturation Point Verification)

*   **理論與物理意義**：
    *   當注入率不斷提高，總有一條通道 (Channel/Link) 會最先達到 100% 的使用率，這條通道就是「熱點 (Hotspot)」。一旦熱點滿載，背壓 (Backpressure) 就會擴散，導致整個網路的延遲呈指數型上升，這就是「飽和 (Saturation)」。
*   **Python (`dse_tools/core/metrics.py`) 實作**：
    *   **方法**：`analyze_channel_load(G, routing_algorithm)` 函式。
    *   **計算**：模擬每個節點對每個節點發送 1 單位的封包。依照指定的路由演算法 (如 XY routing) 描繪出每一條路徑，並將路徑上經過的邊 (Edge) 計數加一。最後找出計數最大的邊，即為 `Max Load`。
    *   **推導**：`理論最大注入率 (Theory Max Rate) = 1 / (Max Load / 總節點數)` *（假設每個節點機率均等）*。
*   **BookSim 驗證方式**：
    *   **設定**：使用 Python Runner (`verify_cross_correlation.py`) 對 `injection_rate` 進行從 `0.01` 到 `0.99` 的逐步掃描 (Sweep)。
    *   **觀察指標**：找出延遲曲線斜率突然變陡 (趨近垂直)，或者 BookSim 判定為 `unstable` 的那個 `injection_rate` 點。
    *   **比對邏輯**：將 BookSim 找出的「實際飽和點 (Actual Saturation Rate)」與 Python 推導的「理論最大注入率」進行對比。正常情況下，BookSim 的實際飽和點會稍微**小於或等於**理論值。因為理論值假設了完美的流量排程，而實際硬體會有 VC 配置不當或 Switch Allocator 的氣泡 (Bubbles) 產生。如果實際飽和點大於理論值，表示理論計算的路由路徑有誤（例如沒有正確考慮負載平衡）。

### 2.3 極限吞吐量驗證 (Throughput Verification)

*   **理論與物理意義**：
    *   二分頻寬 (Bisection Bandwidth) 是將網路切成對半時，跨越切面的最少實體連線數。它決定了網路兩端互相通訊的物理極限。
*   **Python (`dse_tools/core/metrics.py`) 實作**：
    *   **方法**：`calculate_bisection_bandwidth(G)` 函式。
    *   **計算**：針對規則拓撲直接套用數學公式。例如 $k \times k$ Mesh 的切面邊數是 $2k$ (考慮雙向)；Ring 的切面必定切斷 $4$ 條單向連線。
*   **BookSim 驗證方式**：
    *   **觀察指標**：當網路進入飽和狀態（延遲無限大）時，系統能成功送達終點的極限封包速率。這可由「實際飽和點 × 總節點數」來近似估算總吞吐量。
    *   **比對邏輯**：二分頻寬越大，網路理論上能容納的整體吞吐量就越高。在散佈圖中，Python 的 `Bisection BW` 必須與 BookSim 的 `Total Throughput` 呈現高度正相關。

---

## 3. 自動化比對管線 (Automated Correlation Pipeline)

為了確保上述三個層次的數值都正確無誤，本專案的 `verify_cross_correlation.py` 腳本扮演了核心的稽核角色：

1.  **資料生成**：它會根據 `verification_sweep.yaml` 中定義的各種拓撲大小 (Mesh 2x2 到 6x6, Ring 4 到 24 等)，**先**呼叫 Python `metrics.py` 算出所有理論值，**再**自動呼叫 BookSim 執行完整掃描。
2.  **資料對齊**：將同一組拓撲配置下的「理論值」與「BookSim 模擬值」合併存入 `verification_results.json` 的同一個 JSON Object 內。
3.  **統計檢驗**：利用 `numpy.corrcoef` (在 `generate_verify_table.py` 中) 嚴格計算這兩組數列的「皮爾森相關係數 (Pearson Correlation Coefficient)」。如果相關係數小於 0.8，則表示理論分析與實體模擬產生了嚴重的分歧，必須回頭 Review 路由演算法或拓撲連線的正確性。

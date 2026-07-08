# Cycle-Accurate Visualizer 使用與驗證指南

本指南搭配 `ca_visualizer.html` 視覺化工具，幫助您透過實際的 3x3 AI-Processor 擁塞測試情境 (CA_verify case)，以人工視覺方式確認 C++ NoC 模擬器的週期精確行為。

## 🎬 測試情境設計 (3x3 AI-Processor)
本測試情境建立了一個 3 條垂直環 (V0~V2 = Ring 0~2) 與 3 條水平環 (H0~H2 = Ring 3~5) 的網路拓撲。
在 `Cycle 0` 時，我們刻意注入了兩批封包來製造「跨環交會擁塞」：

1. **注入主角群 (F101 ~ F105)**：
   * 起點：垂直環 **Ring 0**, `Station 8`
   * 終點：水平環 **Ring 3**, `Station 4`
   * 路徑：它們會沿著垂直環前進，並在 `Station 0` 的地方透過 **RBRG-L1 橋接器 (BRG_0_3)** 準備跨越到水平環。
2. **注入干擾群 (F201 ~ F210)**：
   * 起點：水平環 **Ring 3**, `Station 10`
   * 終點：水平環 **Ring 3**, `Station 8`
   * 路徑：它們只在水平環上移動，但會經過 Bridge 將主角群注入水平環的入口 (`Ring 3, Station 0`)，藉此霸佔通道。

---

## 🔍 每個 Cycle 的數據行為解析 (HTML 觀看指南)

請在瀏覽器中開啟 `ca_visualizer.html`，並利用工具列的 **Next Cycle** 或 **進度條** 對照以下週期觀察：

*   **Cycle 0 ~ 3 (各自前進)**：
    您會看到垂直環上 F101~F104 魚貫前進；水平環上 F201~F204 也在前進。此時兩路封包井水不犯河水。

*   **Cycle 4 (主角抵達交會點)**：
    F101 抵達垂直環的 `Station 0`，被 Bridge (`BRG_0_3`) 擷取。將滑鼠游標停留在橘色的 Bridge 節點上，您會發現 F101 從環上消失，並成功進入了 Bridge 的 `ingress` 佇列。

*   **Cycle 5 ~ 7 (管線延遲與等待)**：
    這時 F101 在 Bridge 內部經歷 `latency_cycles = 2` 的管線延遲，隨後進入了 `egress` 佇列。
    **發生擁塞 (Congestion)**：在 Cycle 7 時，F101 準備從 Bridge 的 `egress` 注入水平環 (`Ring 3`)。但此時水平環剛好被干擾群 (F204, F205...) 霸佔了！因為水平環沒有空位 (`occupied = true`)，F101 被卡在 `egress` 裡出不去。

*   **Cycle 8 ~ 11 (背壓 Backpressure 發生)**：
    由於 F101 卡在出口，後續的 F102, F103 陸續抵達 Bridge，很快就把 Bridge 的 Queue (深度容量設定為 2) 給塞滿了。
    當 Bridge 滿載後，垂直環上晚到的 F104 與 F105 因為進不去 Bridge，只能繼續留在垂直環上。這就是 Bufferless 網路特有的 **Deflection (偏折)** 行為！在畫面上可以清楚看到 F104, F105 被迫在垂直環上繼續繞圈。

*   **Cycle 12 之後 (擁塞解除，成功跨環)**：
    隨著干擾群 (F2xx 系列) 走完並在 `Ring 3, Station 8` 被陸續 Eject 掉，水平環終於空出了位置。
    此時 Bridge 的 `egress` 開始將 F101, F102 注入水平環，主角群順利跨環。

*   **Cycle 20 (全數抵達)**：
    所有的 Flit 最終都順利抵達目的地。主角群 (F1xx) 靜靜躺在 `R3_S4` 的 `eject_q` 中，而干擾群 (F2xx) 則躺在 `R3_S8` 的 `eject_q` 中。

---

## ✅ 驗證結論
透過本視覺化工具的人工比對，我們可以 100% 確定：
1. **跨環路由 (Bridge Routing)** 判斷正確無誤。
2. **管線延遲 (Pipeline Delay)** 與 **佇列深度 (Queue Depth)** 的硬體限制運作正常。
3. 最重要的是，精準模擬出了 **無緩衝區網路 (Bufferless Network)** 遇到熱點時的 **背壓與偏折 (Backpressure & Deflection)** 物理現象！

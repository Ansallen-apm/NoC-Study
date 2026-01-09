# NoC Architecture (NoC 架構)

## 1. Top Level Architecture (頂層架構)
*   **Topology (拓撲)**: 2D Mesh (Configurable Dimensions, default 4x4). (2D 網狀結構，可配置尺寸，預設 4x4。)
*   **Routing (路由)**: XY Routing (Deterministic). (XY 路由，確定性路由。)
    *   Route X first, then Y. (先走 X 方向，再走 Y 方向。)
*   **Flow Control (流量控制)**: Store-and-Forward (for simplicity in first version) or Credit-Based. (儲存轉發 - 初版簡化，或信用制。)
    *   *Decision*: We will implement a simplified **packet-switched** mechanism with buffer availability checks. (決定：我們將實作一個簡化的**封包交換**機制，並檢查緩衝區可用性。)
*   **Switching (交換方式)**: Packet Switching. (封包交換。)

## 2. Micro-Architecture (Router) (路由器微架構)
*   **Ports (埠)**: 5 Ports (Local, North, East, South, West). (5 個埠：本地、北、東、南、西。)
*   **Input Buffers (輸入緩衝)**: FIFO queue at each input port. (每個輸入埠都有 FIFO 佇列。)
*   **Arbiter (仲裁器)**: Round-Robin Arbitration for switch traversal. (用於開關遍歷的輪詢仲裁。)
*   **Crossbar (縱橫式交換開關)**: Fully connected (or implicitly handled by muxes). (全連接，或由多工器隱式處理。)

## 3. Bus & Signals (匯流排與訊號)
*   **Data Width (資料寬度)**: 32-bit payload. (32 位元負載。)
*   **Control Signals (控制訊號)**: Valid, Ready (Handshake). (Valid, Ready 握手訊號。)

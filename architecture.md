# NoC Architecture Design & Theory (片上網路架構設計與理論)

This document provides a broad overview of Network-on-Chip (NoC) architecture design, discussing various topologies and routing algorithms. It also details the theoretical formulas used to evaluate NoC performance during the Design Space Exploration (DSE) phase.
(本文檔提供了片上網路 (NoC) 架構設計的廣泛概述，討論了各種拓撲結構和路由演算法。它還詳細介紹了在架構探索 (DSE) 階段用於評估 NoC 效能的理論公式。)

---

## 1. Topologies (拓撲結構)

The topology defines the physical layout and connection among nodes (routers) in the NoC.
(拓撲結構定義了 NoC 中節點（路由器）之間的實體佈局和連接方式。)

### 1.1 2D Mesh (二維網格)
A grid-like structure where each router is connected to its North, South, East, and West neighbors. It is the most common NoC topology due to its simple planar layout and scalability.
(一種類似網格的結構，每個路由器都與其北、南、東、西的鄰居相連。由於其簡單的平面佈局和可擴展性，它是最常見的 NoC 拓撲。)

### 1.2 Torus (環面網格)
Similar to a 2D Mesh, but edge nodes wrap around to connect to the opposite edge, reducing the average distance but increasing wire length complexity.
(類似於 2D Mesh，但邊緣節點會環繞連接到對面的邊緣，從而縮短平均距離，但增加了佈線長度的複雜性。)

### 1.3 Ring (環形)
Routers are connected in a circular closed loop. Simple and low-cost but scales poorly for large numbers of nodes.
(路由器連接成一個封閉的圓環。簡單且成本低，但對於大量節點的擴展性較差。)

### 1.4 Tree / Fat-Tree (樹狀 / 胖樹)
Nodes are arranged hierarchically. Fat-tree increases the link bandwidth closer to the root to prevent bottlenecks.
(節點呈階層狀排列。胖樹 (Fat-tree) 會增加靠近根部節點的連結頻寬，以防止效能瓶頸。)

---

## 2. Routing Algorithms (路由演算法)

Routing algorithms determine the path a packet takes from source to destination.
(路由演算法決定封包從來源到目的地的傳輸路徑。)

### 2.1 Deterministic Routing (確定性路由)
The path is completely determined by the source and destination addresses, ignoring network conditions.
(路徑完全由來源和目的地地址決定，忽略網路狀況。)
*   **XY Routing (Dimension-Order Routing)**: Packets travel first along the X-axis, then along the Y-axis. It is inherently deadlock-free in a 2D Mesh.
    (封包先沿 X 軸移動，再沿 Y 軸移動。在 2D Mesh 中，它本質上是不會產生死結的。)

### 2.2 Adaptive Routing (自適應路由)
The path can change dynamically based on network conditions (e.g., congestion or faulty links).
(路徑可以根據網路狀況（例如擁塞或故障連結）動態改變。)
*   **Minimal Adaptive Routing**: Chooses the shortest path but can alternate between different minimal paths to avoid congestion.
    (選擇最短路徑，但可以在不同的最短路徑之間切換以避免擁塞。)
*   **Fully Adaptive Routing**: Can route packets away from the destination temporarily (non-minimal) to bypass severe congestion.
    (可以暫時將封包引導遠離目的地（非最短路徑），以繞過嚴重的擁塞。)

---

## 3. Theoretical Formulas & Analysis (理論公式與分析)

These theoretical metrics are calculated (often via Python scripts) to establish performance baselines before running cycle-accurate simulations.
(這些理論指標通常會透過 Python 腳本計算出來，以便在執行週期精確的模擬之前建立效能基準。)

### 3.1 Bisection Bandwidth (二分頻寬)

**Definition (定義)**: The minimum bandwidth available when the network is divided into two equal halves. It represents the worst-case communication capacity across the network.
(當網路被分成相等的兩半時，可用的最小頻寬。它代表了跨網路在最壞情況下的通訊能力。)

**Formula for $k \times k$ 2D Mesh (對於 $k \times k$ 2D Mesh 的公式)**:
Let $c$ be the channel bandwidth (bits/cycle or flits/cycle).
The cut divides the mesh into two $k \times (k/2)$ sub-meshes. The number of links crossing the cut is $2k$ (considering bidirectional links).
(設 $c$ 為通道頻寬（位元/週期 或 flit/週期）。切割線將網格分成兩個 $k \times (k/2)$ 的子網格。穿過切割線的連結數量為 $2k$（考慮雙向連結）。)

$$ Bisection\_Bandwidth_{Mesh} = 2 \times k \times c $$

### 3.2 Channel Load / Link Utilization (通道負載 / 連結利用率)

**Definition (定義)**: The expected amount of traffic passing through a specific link. Highly dependent on the traffic pattern (e.g., Uniform Random, Bit-Complement) and the routing algorithm.
(預期通過特定連結的流量。高度依賴於流量模式（例如：均勻隨機、位元互補）和路由演算法。)

**Calculation method (計算方法)**:
For a given Traffic Matrix $\Lambda$ where $\lambda_{i,j}$ is the packet injection rate from node $i$ to $j$:
(對於給定的流量矩陣 $\Lambda$，其中 $\lambda_{i,j}$ 是從節點 $i$ 到 $j$ 的封包注入率：)

$$ Load(link_e) = \sum_{i,j} \lambda_{i,j} \times P(link_e \in Path_{i \to j}) $$
Where $P$ is the probability (1 or 0 for deterministic routing) that the path from $i$ to $j$ uses link $e$.
(其中 $P$ 是從 $i$ 到 $j$ 的路徑使用連結 $e$ 的機率（對於確定性路由為 1 或 0）。)

### 3.3 Hot Spots (熱點分析)

**Definition (定義)**: A node or link that experiences significantly higher traffic volume than the network average, causing congestion.
(流量顯著高於網路平均水準，從而導致擁塞的節點或連結。)

**Analysis (分析方式)**:
By calculating the Channel Load for all links, the hot spot is simply the link with the maximum load:
(透過計算所有連結的通道負載，熱點即是具有最大負載的連結：)

$$ HotSpot\_Load = \max_{e \in Links} ( Load(link_e) ) $$
If $HotSpot\_Load > Capacity$, the network will saturate. The theoretical saturation throughput is inversely proportional to the maximum channel load.
(如果熱點負載大於連結容量，網路就會飽和。理論飽和吞吐量與最大通道負載成反比。)

### 3.4 Average Distance / Hop Count (平均距離 / 跳數)

**Definition (定義)**: The average number of links a packet traverses from source to destination under uniformly distributed traffic.
(在均勻分佈的流量下，封包從來源到目的地平均穿越的連結數量。)

**Formula for $k \times k$ 2D Mesh (對於 $k \times k$ 2D Mesh 的公式)**:
$$ H_{avg} = \frac{2k}{3} $$
*(Note: This is an approximation for large $k$; exact formula depends on whether node self-traffic is included).*
*(註：這是當 $k$ 很大時的近似值；精確公式取決於是否包含節點對自身的流量)。*

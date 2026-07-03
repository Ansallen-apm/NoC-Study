# Cycle-Accurate C++ NoC Model 實作規劃

> 參考論文：**Application Defined On-chip Networks for Heterogeneous Chiplets: An Implementation Perspective**  
> 目標：建立一個 **cycle-accurate C++ NoC simulator / model**，模擬論文中的 **bufferless multi-ring NoC**，包含 cross station microarchitecture、I/E tag、RBRG-L1/L2、SWAP deadlock recovery，以及 Server-CPU / AI-Processor 兩種拓撲。

---

## 1. Model 目標與範圍

### 1.1 主要目標

建立一個 **cycle-accurate C++ NoC 模型**，用來模擬 heterogeneous chiplet-based SoC 中的 bufferless multi-ring NoC。

此模型應支援：

- Bufferless ring / multi-ring NoC
- Half-ring / full-ring
- Cross Station
- Node Interface
- Inject Queue / Eject Queue
- I-tag：避免 injection starvation
- E-tag：避免 ejection starvation / livelock
- RBRG-L1：die 內部的 cross-ring bridge
- RBRG-L2：die-to-die / chiplet-to-chiplet bridge
- SWAP-based deadlock recovery
- Server-CPU latency-oriented topology
- AI-Processor bandwidth-oriented topology
- Synthetic traffic 與 trace-driven traffic
- Per-cycle latency、bandwidth、utilization、deadlock 統計

### 1.2 初版建議簡化項目

論文中的架構以 AMBA5 CHI 為基礎，但第一版不建議直接實作完整 CHI protocol。建議先實作 **CHI-like transaction abstraction**：

- `ReadReq`
- `WriteReq`
- `SnoopReq`
- `DataResp`
- `CompAck`
- `DMARead`
- `DMAWrite`

原因是初版的核心目標應放在 NoC transport behavior：flit 如何在 ring 上移動、如何跨 ring / 跨 die、如何處理 starvation / deadlock。Server-CPU 與 AI-Processor 的 NoC transaction 可以先抽象成 cache-line granularity 的 independent flit transaction。

---

## 2. Simulator 整體架構

建議採用 cycle-based simulation framework，每個 component 具有 `tick()` / `tock()` 兩階段：

```cpp
class Component {
public:
    virtual void tick() = 0;   // 計算本 cycle 的 next-state decision
    virtual void tock() = 0;   // 在 clock edge commit state
    virtual ~Component() = default;
};
```

### 2.1 Top-Level Components

```text
Simulator
 ├── Topology
 │    ├── Ring
 │    ├── CrossStation
 │    ├── NodeInterface
 │    ├── RBRG_L1
 │    └── RBRG_L2
 ├── TrafficGenerator
 │    ├── ServerTrafficGenerator
 │    └── AITrafficGenerator
 ├── ProtocolAgent
 │    ├── CPUClusterAgent
 │    ├── AICoreAgent
 │    ├── L2Agent
 │    ├── L3TagAgent
 │    ├── L3DataAgent
 │    ├── LLCAgent
 │    ├── DDRAgent
 │    └── HBMAgent
 ├── DieToDieLink
 ├── DeadlockMonitor
 ├── StatCollector
 └── TraceDumper
```

### 2.2 每個 Cycle 的執行順序

```text
Cycle N:

1. Traffic generator 產生新的 requests。
2. Agent 將 request 轉成 flit，並推入 source node 的 InjectQueue。
3. RBRG-L2 更新 deadlock detection counter。
4. CrossStation 讀取 incoming ring slots。
5. CrossStation 決定 eject / pass-through / inject / swap。
6. RBRG-L1 / RBRG-L2 執行 bridge queue arbitration 與 route compute。
7. Die-to-die link pipeline 前進一個 cycle。
8. Ring slot 移動到下一個 station。
9. 所有 component 執行 tock() commit state。
10. StatCollector sample counters / histogram。
11. 檢查 simulation stop condition。
```

重點：所有 component 應使用雙 buffer 或 next-state 設計，避免同一個 cycle 中因為更新順序導致非預期行為。

---

## 3. 基本資料結構

### 3.1 Flit

第一版建議一個 NoC transaction 對應一個 flit。

```cpp
enum class FlitType {
    ReadReq,
    WriteReq,
    SnoopReq,
    DataResp,
    CompAck,
    DMARead,
    DMAWrite
};

enum class Direction {
    CW,
    CCW
};

struct Flit {
    uint64_t id = 0;

    int src_node = -1;
    int dst_node = -1;

    int src_ring = -1;
    int dst_ring = -1;
    int current_ring = -1;

    FlitType type = FlitType::ReadReq;
    Direction dir = Direction::CW;

    uint64_t create_cycle = 0;
    uint64_t inject_cycle = 0;
    uint64_t eject_cycle = 0;

    int hop_count = 0;
    int deflect_count = 0;
    int ring_change_count = 0;

    bool valid = false;

    // Optional CHI-like fields
    uint32_t txn_id = 0;
    uint32_t qos = 0;
    uint32_t logical_class = 0;
};
```

### 3.2 Ring Slot

Ring 可視為一組 circular slot。每個 slot 每 cycle 最多承載一個 flit。

```cpp
struct RingSlot {
    bool occupied = false;
    Flit flit;

    // I-tag：保留給 injection 失敗的 flit
    bool i_tag = false;
    int i_tag_owner_station = -1;
    uint64_t i_tag_flit_id = 0;

    // E-tag：保留給 ejection 失敗的 flit
    bool e_tag = false;
    int e_tag_owner_station = -1;
    uint64_t e_tag_flit_id = 0;
};
```

---

## 4. Ring Microarchitecture

### 4.1 Half-Ring

Half-ring 是單方向 ring，通常可先模擬為 clockwise loop。

```cpp
class Ring {
public:
    int ring_id;
    int num_stations;
    bool bidirectional;

    std::vector<RingSlot> curr_cw_slots;
    std::vector<RingSlot> next_cw_slots;

    void tick();
    void tock();
};
```

### 4.2 Full-Ring

Full-ring 具有兩個方向：

- Clockwise loop
- Counterclockwise loop

```cpp
class Ring {
public:
    std::vector<RingSlot> curr_cw_slots;
    std::vector<RingSlot> next_cw_slots;

    std::vector<RingSlot> curr_ccw_slots;
    std::vector<RingSlot> next_ccw_slots;
};
```

### 4.3 Direction Selection

Full-ring 中，flit injection 時應選擇最短方向。

```cpp
Direction choose_direction(int src_pos, int dst_pos, int ring_size) {
    int cw_dist = (dst_pos - src_pos + ring_size) % ring_size;
    int ccw_dist = (src_pos - dst_pos + ring_size) % ring_size;
    return cw_dist <= ccw_dist ? Direction::CW : Direction::CCW;
}
```

### 4.4 Ring Slot Movement

每個 cycle，ring slot 移動到下一個 station。

```text
CW direction:
next_slot[(i + 1) % N] = curr_slot[i]

CCW direction:
next_slot[(i - 1 + N) % N] = curr_slot[i]
```

這是 cycle-accurate ring fabric 的核心。

---

## 5. Cross Station Microarchitecture

### 5.1 Cross Station 結構

每個 cross station 最多可連接兩個 local devices。

```text
CrossStation
 ├── Reg_In_CW
 ├── Reg_Out_CW
 ├── Reg_In_CCW
 ├── Reg_Out_CCW
 ├── NodeInterface[0]
 │    ├── InjectQueue
 │    └── EjectQueue
 ├── NodeInterface[1]
 │    ├── InjectQueue
 │    └── EjectQueue
 └── ControlLogic
```

### 5.2 Node Interface

```cpp
class InjectQueue {
public:
    size_t capacity;
    std::deque<Flit> q;

    bool can_push() const;
    bool can_pop() const;
    Flit& front();
    void push(const Flit& f);
    void pop();
};

class EjectQueue {
public:
    size_t capacity;
    std::deque<Flit> q;

    bool has_space() const;
    bool can_accept(const Flit& f) const;
    void push(const Flit& f);
};

class NodeInterface {
public:
    InjectQueue inject_q;
    EjectQueue eject_q;
};
```

### 5.3 Cross Station Priority Rule

建議 priority 如下：

```text
1. On-the-fly flit 最高優先權。
2. 若 incoming flit 到達目的地且 EjectQueue 有空間，則 eject。
3. 若 incoming flit 到達目的地但 EjectQueue 滿，則 pass-through / deflect，並建立 E-tag。
4. 若 output slot 為空且 I-tag 與本站 / flit match，則 inject reserved flit。
5. 若 output slot 為空且沒有 reservation，則使用 round-robin 從 local InjectQueue 選一個 flit injection。
6. 若沒有任何 flit injection，slot 保持 empty。
```

### 5.4 Round-Robin Injection Arbitration

```cpp
int rr_ptr = 0;

int choose_inject_port() {
    for (int k = 0; k < 2; ++k) {
        int port = (rr_ptr + k) % 2;
        if (node_if[port].inject_q.can_pop()) {
            rr_ptr = (port + 1) % 2;
            return port;
        }
    }
    return -1;
}
```

---

## 6. I-Tag Injection Reservation

### 6.1 目的

當某個 flit 因為 output slot 被 on-the-fly flit 佔用而 injection 失敗時，cross station 會在 moving slot 上附加 I-tag。當該 slot 回到此 station 時，slot 會保留給原本 injection 失敗的 flit。

### 6.2 State

```cpp
struct InjectReservation {
    bool valid = false;
    uint64_t flit_id = 0;
    int station_id = -1;
    Direction dir = Direction::CW;
};
```

### 6.3 行為

```text
Cycle T:
- Station S 想要 inject Flit A。
- Output slot 已被 Flit B 佔用。
- Flit A injection 失敗。
- Station S 將 I-tag metadata 附在該 moving slot 上。

之後：
- tagged slot 回到 Station S。
- 若 Flit A 仍在 InjectQueue head，Station S 將 Flit A inject 到此 slot。
- 清除 I-tag。
```

### 6.4 Modeling Note

建議將 I-tag 建模為 `RingSlot` 的 metadata，而不是 station-local flag，因為其語意更接近「隨 slot 移動的 reservation」。

---

## 7. E-Tag Ejection Reservation

### 7.1 目的

當 flit 到達目的地但 EjectQueue 已滿，flit 必須繼續在 ring 上移動。E-tag 用於保留未來的 EjectQueue 空間給此 deflected flit。

### 7.2 State

```cpp
struct EjectReservation {
    bool valid = false;
    uint64_t flit_id = 0;
    int dst_station = -1;
    int dst_node = -1;
    Direction dir = Direction::CW;
};
```

### 7.3 行為

```text
If incoming flit reaches destination:
    if EjectQueue has space:
        eject flit
    else:
        flit.deflect_count++
        pass flit through
        create E-tag reservation

When EjectQueue has free space:
    reserve it for tagged flit

When tagged flit returns:
    eject flit into reserved EjectQueue entry
    clear E-tag
```

---

## 8. RBRG-L1：Intra-Die Ring Bridge

### 8.1 角色

RBRG-L1 用於同一個 die 內部兩條 ring 之間的轉接，例如 AI topology 中 vertical ring 與 horizontal ring 的 intersection。

主要責任：

- 從 source ring eject flit
- 暫存 flit
- 計算 target ring 與 direction
- 將 flit inject 到 destination ring
- 支援簡單 cross-ring routing

### 8.2 建議 Microarchitecture

```text
RBRG-L1
 ├── IngressQueue from Ring A
 ├── IngressQueue from Ring B
 ├── EgressQueue to Ring A
 ├── EgressQueue to Ring B
 ├── RouteCompute
 ├── Arbiter
 └── PipelineRegisters
```

### 8.3 Pipeline

第一版建議用 3-stage model：

```text
Stage 0: 從 source ring eject 到 bridge ingress queue
Stage 1: Route computation + arbitration
Stage 2: Inject 到 destination ring
```

建議參數：

```yaml
rbrg_l1_latency_cycles: 2
rbrg_l1_queue_depth: 4
```

### 8.4 AI Routing

AI-Processor topology 中：

```text
AI cores 放在 vertical rings。
L2 / LLC / HBM nodes 放在 horizontal rings。
任一 request 最多只需一次 ring change。
可使用 X-Y 或 Y-X style routing。
```

範例：

```text
AICore vertical ring
    → 移動到指定 RBRG-L1
    → 切換到 horizontal ring
    → 到達 L2 / LLC / HBM destination
```

---

## 9. RBRG-L2：Inter-Die / Inter-Chiplet Bridge

### 9.1 角色

RBRG-L2 用於不同 die / chiplet 之間的 ring 連接。

主要責任：

- Inter-die buffering
- Route computation
- Backpressure / credit control
- Die-to-die link modeling
- Deadlock detection
- SWAP-based deadlock recovery

### 9.2 建議 Microarchitecture

```text
RBRG-L2
 ├── LocalRingRxQueue
 ├── LocalRingTxQueue
 ├── RemoteLinkTxBuffer
 ├── RemoteLinkRxBuffer
 ├── ReservedTxBufferForSWAP
 ├── CreditManager
 ├── DeadlockDetector
 ├── DRMController
 └── RouteCompute
```

### 9.3 Die-to-Die Link Model

```cpp
class DieToDieLink : public Component {
public:
    int latency_cycles;
    int width_flits_per_cycle;
    int credit_depth;

    std::vector<std::deque<Flit>> pipeline;

    void tick() override;
    void tock() override;
};
```

建議參數：

```yaml
d2d_latency_cycles: 4
d2d_bandwidth_flits_per_cycle: 1
d2d_credit_depth: 16
```

---

## 10. SWAP-Based Deadlock Recovery

### 10.1 Deadlock 條件

當 RBRG-L2 attached cross station 連續多個 cycles injection 失敗，超過設定 threshold 後，可視為進入可能 deadlock 狀態。

```cpp
if (consecutive_inject_fail_cycles > deadlock_threshold) {
    enter_deadlock_resolution_mode();
}
```

建議參數：

```yaml
deadlock_threshold_cycles: 64
```

### 10.2 DRM State Machine

```cpp
enum class DRMState {
    Normal,
    Detecting,
    DeadlockResolution,
    Recovering
};
```

### 10.3 SWAP 機制

```text
DRM active 時：

1. 啟用 RBRG-L2 reserved TX buffer。
2. 從 EjectQueue 搬一個 flit 到 reserved TX buffer。
3. 因此釋放一個 EjectQueue entry。
4. Incoming traversing flit eject 到剛釋放的 EjectQueue entry。
5. InjectQueue head flit 進入 traversing flit 原本佔用的 ring slot。
6. Ejection 與 injection 在同一個 cycle 發生。
7. 此事件計為一個 SWAP event。
8. 當 TX buffer occupancy 低於 recovery threshold，退出 DRM。
```

### 10.4 Pseudocode

```cpp
void CrossStation::process_drm_swap() {
    if (!drm_active) return;

    if (eject_q.full() && rbrg_l2.reserved_tx_has_space()) {
        Flit victim = eject_q.pop_oldest();
        rbrg_l2.reserved_tx_push(victim);
    }

    if (incoming_slot.occupied &&
        incoming_flit_wants_to_eject_here(incoming_slot.flit) &&
        eject_q.has_space() &&
        inject_q.can_pop()) {

        Flit traversing = incoming_slot.flit;
        Flit injecting = inject_q.front();
        inject_q.pop();

        eject_q.push(traversing);
        incoming_slot.flit = injecting;

        stats.swap_count++;
    }
}
```

### 10.5 Deadlock 統計

建議記錄：

```text
- deadlock_detected_count
- total_drm_cycles
- swap_count
- reserved_tx_buffer_occupancy
- max_consecutive_inject_fail_cycles
```

---

## 11. Server-CPU Topology Model

### 11.1 設計目標

Server-CPU topology 以 **low latency** 為主要 KPI。

建議 mapping：

```text
CPU Compute Die / CCD:
- Full ring
- CPU clusters
- L3 tag cache
- L3 data cache
- LLC
- DDR controller
- RBRG-L2 endpoints

I/O Die / IOD:
- Half ring
- PCIe
- Ethernet
- Protocol Adapter
- Service accelerators
- RBRG-L2 endpoints
```

### 11.2 Example YAML Config

```yaml
topology: server_cpu
flit_bytes: 64

rings:
  - id: 0
    die: CCD0
    type: full
    stations: 32
  - id: 10
    die: IOD0
    type: half
    stations: 16

nodes:
  - id: 0
    type: CPU_CLUSTER
    ring: 0
    station: 0
  - id: 1
    type: L3_TAG
    ring: 0
    station: 4
  - id: 2
    type: L3_DATA
    ring: 0
    station: 8
  - id: 3
    type: DDRC
    ring: 0
    station: 12
  - id: 100
    type: PCIE
    ring: 10
    station: 2
  - id: 101
    type: ETHERNET
    ring: 10
    station: 6

bridges:
  - type: RBRG_L2
    local_ring: 0
    remote_ring: 10
    local_station: 16
    remote_station: 8
    d2d_latency_cycles: 4
```

### 11.3 Server Traffic Models

建議實作下列 experiments：

```text
1. Single core DDR access latency:
   - Target core 發 DDR read。
   - Background cores 發 read/write traffic。
   - Sweep background traffic load。

2. Cache state latency:
   - Core-0 將 data block 設為 M/E/S-like synthetic state。
   - Core-1 access 同一 data block。
   - 量測 NoC-level access latency。

3. Bandwidth saturation:
   - 多個 CPU clusters 對 DDR/LLC inject traffic。
   - 量測 aggregate accepted bandwidth。
```

---

## 12. AI-Processor Topology Model

### 12.1 設計目標

AI-Processor topology 以 **aggregate bandwidth** 與 **bandwidth equilibrium** 為主要 KPI。

建議 mapping：

```text
Vertical rings:
- AI cores

Horizontal rings:
- L2 slices
- LLC
- HBM controllers

RBRG-L1:
- 放在 vertical/horizontal intersections

RBRG-L2:
- 如需 I/O die 擴充，連接 AI compute die 與 I/O die
```

### 12.2 Example YAML Config

```yaml
topology: ai_processor
flit_bytes: 64

vertical_rings:
  count: 8
  type: half
  stations_per_ring: 32

horizontal_rings:
  count: 8
  type: half
  stations_per_ring: 32

rbrg_l1:
  at_each_intersection: true
  queue_depth: 4
  latency_cycles: 2

nodes:
  vertical:
    - type: AICORE
      count_per_ring: 8
  horizontal:
    - type: L2
      count_per_ring: 4
    - type: LLC
      count_per_ring: 2
    - type: HBMC
      count_per_ring: 1

routing:
  mode: XY
```

### 12.3 AI Traffic Models

建議實作與論文評估方式相近的 synthetic traffic：

```text
Read/write ratio sweep:
- 1:1
- 2:1
- 4:1
- 3:2
- 1:0
- 0:1

Traffic classes:
- AICore → LLC request
- LLC → L2 lookup / directory hit
- L2 → AICore data response
- L2 ↔ HBM via LLC on miss
- DMA traffic
```

### 12.4 Bandwidth Equilibrium Metrics

每個 probe 建議記錄：

```text
- probe_bw_avg
- probe_bw_p5
- probe_bw_p50
- probe_bw_p95
- min_probe_bw / max_probe_bw
- ring_utilization
- bridge_utilization
```

---

## 13. 統計與 Metrics

### 13.1 Latency

```text
inject_latency = inject_cycle - create_cycle
network_latency = eject_cycle - inject_cycle
end_to_end_latency = eject_cycle - create_cycle
```

建議統計：

```text
- average latency
- p50 latency
- p95 latency
- p99 latency
- max latency
```

### 13.2 Bandwidth

```text
flits_per_cycle = ejected_flits / total_cycles
bytes_per_cycle = flits_per_cycle * flit_bytes
```

轉換成 TB/s：

```text
bandwidth_Bps = bytes_per_cycle * frequency_Hz
bandwidth_TBps = bandwidth_Bps / 1e12
```

Example：

```yaml
frequency_ghz: 3.0
flit_bytes: 64
```

### 13.3 Contention

```text
- injection_fail_count
- ejection_fail_count
- deflection_count
- average_deflection_per_flit
- bridge_queue_occupancy_avg
- bridge_queue_occupancy_max
```

### 13.4 Deadlock / SWAP

```text
- deadlock_detected_count
- drm_entry_count
- total_drm_cycles
- swap_count
- reserved_tx_buffer_max_occupancy
```

---

## 14. Physical Modeling Parameters

論文中特別強調 `distance per cycle` 是 NoC co-design 的重要 metric。建議模型中保留 physical parameter：

```yaml
frequency_ghz: 3.0
flit_bytes: 64
station_spacing_um: 1800
cycles_per_ring_segment: 1
```

未來可擴充：

```text
physical_distance_um → inserted pipeline stations → latency cycles
```

建議將 physical parameters 與 logical topology 分離，方便做 architecture / implementation tradeoff sweep。

---

## 15. Implementation Phases

### Phase 0 — Simulator Skeleton

Deliverables：

```text
- Component base class
- Simulator cycle loop
- Config parser
- StatCollector
- TraceDumper
- Basic unit test framework
```

### Phase 1 — Single Half-Ring

Deliverables：

```text
- Ring slot movement
- Cross station pass-through
- InjectQueue / EjectQueue
- Basic injection and ejection
- Latency measurement
```

Validation：

```text
No-contention latency = ring distance + configured pipeline overhead
```

### Phase 2 — Full-Ring

Deliverables：

```text
- CW / CCW movement
- Shortest-path direction selection
- Per-direction injection arbitration
```

Validation：

```text
Latency should equal min(CW distance, CCW distance)
```

### Phase 3 — I-Tag / E-Tag

Deliverables：

```text
- I-tag slot reservation
- E-tag ejection reservation
- Starvation / livelock stress test
```

Validation：

```text
在 heavy traffic 下，不應有 flit 永遠停在 InjectQueue，也不應有 flit 永遠在 ring 上繞圈。
```

### Phase 4 — RBRG-L1 Multi-Ring

Deliverables：

```text
- Vertical / horizontal ring topology
- RBRG-L1 queues
- Cross-ring routing
- XY / YX routing support
```

Validation：

```text
AICore vertical ring 到 L2 horizontal ring 應只需要一次 ring change。
```

### Phase 5 — RBRG-L2 and Die-to-Die Link

Deliverables：

```text
- RBRG-L2 queueing
- D2D link latency
- Credit / backpressure
- CCD ↔ IOD traffic
```

Validation：

```text
Inter-die latency = source ring latency + RBRG-L2 latency + D2D latency + destination ring latency
```

### Phase 6 — SWAP Deadlock Recovery

Deliverables：

```text
- Deadlock detector
- DRM state machine
- Reserved TX buffer
- Same-cycle eject/inject SWAP behavior
```

Validation：

```text
Synthetic two-ring deadlock:
- Without SWAP: no progress
- With SWAP: progress resumes
```

### Phase 7 — Server-CPU Experiments

Deliverables：

```text
- Server topology config
- CPU cluster traffic generator
- DDR / LLC traffic sink
- Background read/write load sweep
```

Output files：

```text
server_latency_vs_load.csv
server_bandwidth.csv
server_inter_chiplet_latency.csv
server_intra_chiplet_latency.csv
```

### Phase 8 — AI-Processor Experiments

Deliverables：

```text
- AI vertical/horizontal multi-ring topology
- AICore / L2 / HBM traffic generators
- Read/write ratio sweep
- Bandwidth probes
```

Output files：

```text
ai_bw_rw_ratio.csv
ai_probe_balance.csv
ai_ring_utilization.csv
ai_bridge_utilization.csv
```

---

## 16. 建議 C++ Directory Layout

```text
nocsim/
 ├── CMakeLists.txt
 ├── include/
 │    ├── component.hpp
 │    ├── flit.hpp
 │    ├── ring.hpp
 │    ├── cross_station.hpp
 │    ├── node_interface.hpp
 │    ├── bridge.hpp
 │    ├── rbrg_l1.hpp
 │    ├── rbrg_l2.hpp
 │    ├── d2d_link.hpp
 │    ├── agent.hpp
 │    ├── traffic_generator.hpp
 │    ├── stats.hpp
 │    └── simulator.hpp
 ├── src/
 │    ├── ring.cpp
 │    ├── cross_station.cpp
 │    ├── rbrg_l1.cpp
 │    ├── rbrg_l2.cpp
 │    ├── d2d_link.cpp
 │    ├── agent.cpp
 │    ├── traffic_generator.cpp
 │    ├── stats.cpp
 │    └── simulator.cpp
 ├── configs/
 │    ├── server_cpu.yaml
 │    └── ai_processor.yaml
 ├── tests/
 │    ├── test_single_ring.cpp
 │    ├── test_full_ring.cpp
 │    ├── test_i_tag.cpp
 │    ├── test_e_tag.cpp
 │    ├── test_rbrg_l1.cpp
 │    ├── test_rbrg_l2.cpp
 │    └── test_swap_deadlock.cpp
 ├── traces/
 └── scripts/
      ├── run_server_sweep.py
      └── run_ai_sweep.py
```

---

## 17. 建議 Class List

```cpp
class Simulator;
class Config;
class StatCollector;

struct Flit;
struct RingSlot;

class Ring : public Component;
class CrossStation : public Component;
class NodeInterface;
class InjectQueue;
class EjectQueue;

class RingBridge : public Component;
class RBRG_L1 : public RingBridge;
class RBRG_L2 : public RingBridge;

class DieToDieLink : public Component;

class Agent : public Component;
class CPUClusterAgent : public Agent;
class AICoreAgent : public Agent;
class L2Agent : public Agent;
class L3TagAgent : public Agent;
class L3DataAgent : public Agent;
class LLCAgent : public Agent;
class MemoryAgent : public Agent;

class TrafficGenerator;
class ServerTrafficGenerator : public TrafficGenerator;
class AITrafficGenerator : public TrafficGenerator;

class Router;
class XYRouter : public Router;
class ShortestPathRouter : public Router;
class TableRouter : public Router;
```

---

## 18. Validation Checklist

### 18.1 Functional Validation

- [ ] Flit injection 正確。
- [ ] Flit ejection 正確。
- [ ] Ring slot 每 cycle 只移動一個 station。
- [ ] Full-ring 正確選擇 shortest direction。
- [ ] Round-robin arbitration 不會餓死某個 local port。
- [ ] I-tag 可避免 injection starvation。
- [ ] E-tag 可避免 endless ejection deflection。
- [ ] RBRG-L1 可完成 intra-die ring change。
- [ ] RBRG-L2 可完成 inter-die transfer。
- [ ] D2D link latency 符合設定。
- [ ] SWAP 可打破 synthetic deadlock。
- [ ] 沒有 flit duplicated。
- [ ] 沒有 flit lost。

### 18.2 Cycle-Accuracy Validation

- [ ] Empty-network latency 符合預期 ring distance。
- [ ] Bridge latency 符合 configured pipeline latency。
- [ ] D2D latency 符合 configured link latency。
- [ ] 每個 slot 每 cycle 最多只有一個 flit。
- [ ] 只有允許的情況下能 same-cycle ejection / injection。
- [ ] SWAP event 必須 atomic update eject / inject state。

### 18.3 Performance Validation

- [ ] 負載接近 saturation 時 latency 會急遽上升。
- [ ] AI read/write ratio 改變時 aggregate bandwidth 會變化。
- [ ] Saturation 下 ring utilization 接近期望上限。
- [ ] AI bandwidth probes 顯示分佈均衡。
- [ ] Server traffic 顯示 DDR latency 受 background load 影響。

---

## 19. 建議 Milestone Schedule

| Week | Goal | Output |
|---:|---|---|
| 1 | Simulator skeleton | Empty cycle loop、config、stats |
| 2 | Single half-ring | Basic flit latency |
| 3 | Full-ring | CW/CCW shortest routing |
| 4 | I-tag / E-tag | Starvation / livelock tests |
| 5 | RBRG-L1 | AI-style vertical/horizontal routing |
| 6 | RBRG-L2 | Chiplet crossing and D2D link |
| 7 | SWAP | Deadlock regression pass |
| 8 | Server topology | Latency competition results |
| 9 | AI topology | Bandwidth and equilibrium results |
| 10 | Calibration and documentation | Paper-like evaluation package |

---

## 20. 建議 First Prototype Path

若希望快速做出有研究價值的 prototype，建議優先走這條路徑：

```text
Full-ring CrossStation
→ shortest-path routing
→ I-tag / E-tag
→ RBRG-L1 vertical-horizontal NoC
→ AI read/write bandwidth sweep
```

原因：

- AI traffic 較容易用 synthetic traffic 建模。
- AI topology 的 vertical/horizontal ring 結構明確。
- KPI 是 bandwidth / equilibrium，不需要一開始就建完整 coherence model。
- Server-CPU evaluation 會牽涉更多 cache hierarchy / CHI-like semantic，可放在第二階段。

---

## 21. Key Risk Items

### 21.1 I-Tag / E-Tag 語意

I-tag / E-tag 的行為要明確定義與測試。

建議：

```text
- 將 I-tag / E-tag 建模為 moving slot metadata。
- 增加 debug trace，記錄 tag create / propagate / consume / clear。
```

### 21.2 SWAP Atomicity

SWAP 必須被建模成 RBRG-L2 attached cross station 的 same-cycle ejection / injection。

建議：

```text
- SWAP 在 CrossStation tick() 中決策。
- tock() 時一起 commit ejection 與 injection。
- 加入 assertion 避免 flit duplication / loss。
```

### 21.3 Bufferless 不代表完全沒有 Queue

Ring datapath 是 bufferless，但模型仍會有：

```text
- InjectQueue
- EjectQueue
- RBRG-L1 queues
- RBRG-L2 queues
- D2D link buffers
- Reserved TX buffer for SWAP
```

### 21.4 Calibration

所有重要 latency / queue depth 都應 parameterized：

```text
- ring segment latency
- cross station latency
- RBRG-L1 latency
- RBRG-L2 latency
- D2D latency
- inject/eject queue depth
- bridge queue depth
- flit size
- clock frequency
```

---

## 22. Minimal Experiment Set

### 22.1 Unit Tests

```text
test_single_ring_latency
test_full_ring_shortest_path
test_injection_rr
test_i_tag_reservation
test_e_tag_reservation
test_rbrg_l1_ring_change
test_rbrg_l2_d2d_latency
test_swap_deadlock_recovery
```

### 22.2 Server Experiments

```text
server_empty_network_latency
server_ddr_latency_under_background_read
server_ddr_latency_under_background_write
server_ddr_latency_under_mixed_background
server_inter_chiplet_latency
server_bandwidth_saturation
```

### 22.3 AI Experiments

```text
ai_rw_ratio_1_1
ai_rw_ratio_2_1
ai_rw_ratio_4_1
ai_rw_ratio_3_2
ai_read_only
ai_write_only
ai_probe_balance
ai_bridge_hotspot
```

---

## 23. Final Deliverables

最終應交付：

```text
1. C++ cycle-accurate NoC simulator
2. YAML topology / config files
3. Microarchitecture unit tests
4. Server-CPU synthetic evaluation
5. AI-Processor synthetic evaluation
6. CSV statistics output
7. Optional visualization scripts
8. README with model assumptions and limitations
```

建議文件：

```text
README.md
docs/
 ├── microarchitecture.md
 ├── routing.md
 ├── swap_deadlock_recovery.md
 ├── server_topology.md
 └── ai_topology.md
```

---

## 24. 總結

這份 implementation plan 的重點是先把論文中的 NoC microarchitecture 行為用 cycle-accurate 方式準確建模，同時避免一開始就陷入完整 CHI protocol 與 full-system cache coherence 的複雜度。

最重要的 microarchitectural mechanisms：

```text
1. Bufferless ring slot movement
2. Cross station priority and arbitration
3. I-tag injection reservation
4. E-tag ejection reservation
5. RBRG-L1 cross-ring routing
6. RBRG-L2 inter-chiplet transfer
7. SWAP-based deadlock recovery
8. Bandwidth and latency statistics
```

完成上述功能並通過 validation 後，再擴充到更完整的 CHI-like protocol model、trace-driven simulation 與 paper-like evaluation。

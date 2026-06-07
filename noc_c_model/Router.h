#ifndef ROUTER_H
#define ROUTER_H

#include <vector>
#include <queue>
#include "Packet.h"
#include "Config.h"
#include "Routing.h"

class Router {
public:
    int id;
    int buffer_size;
    int num_ports;
    int num_vcs;
    RoutingAlgorithm* routing_algo;

    // Input Buffers: Each port has multiple VCs, each VC has a queue of Flits
    // 輸入緩衝區：每個埠有多個虛擬通道 (VC)，每個 VC 都有一個 Flit 佇列
    std::vector<std::vector<std::queue<Flit>>> input_buffers;

    // Double buffering for next cycle arrivals to avoid intra-cycle race conditions
    // 雙重緩衝區：儲存預計在下一個週期到達的 Flit，避免同週期競爭
    std::vector<std::vector<std::queue<Flit>>> next_input_buffers;

    // Track how many flits to pop from input_buffers at the end of the cycle
    // 追蹤在此週期結束時，需要從輸入緩衝區移除多少 Flit (避免執行順序依賴)
    std::vector<std::vector<int>> pending_pops;

    // To store flits that have arrived at this destination (Local Ejection)
    // 儲存已到達此目的地的 Flit (本地彈出)
    std::vector<Flit> ejected_flits;

    // Neighbor pointers and their corresponding ingress ports
    // 相鄰路由器指標與其對應的入口埠
    std::vector<Router*> neighbors;
    std::vector<int> neighbor_ingress_ports;

    Router(int id, int num_ports, int num_vcs, int buf_size, RoutingAlgorithm* algo);
    // Connect a neighbor to a specific direction port (連接特定方向的鄰居)
    void connect(int my_port, Router* neighbor, int neighbor_ingress_port);
    // Inject a flit into the local port (注入 Flit 至本地埠)
    bool inject_flit(Flit f);
    // Evaluate and route packets (階段一：評估與路由封包)
    void evaluate(int current_time);
    // Update buffers for next cycle (階段二：更新緩衝區狀態)
    void update();

    // Switch Allocator State: Which input port gets priority next for each output port
    // 仲裁器狀態：針對每個輸出埠，追蹤下一個擁有優先權的輸入埠 (Round-Robin)
    std::vector<int> arbiter_priority;

    // Hardware Monitors (硬體監控器)
    std::vector<int> port_active_cycles;      // 記錄各通道傳輸資料的週期數 (用於計算 uRate)
    std::vector<long long> port_buffer_depth_acc; // 記錄各通道 Buffer 深度的累加值 (用於計算平均深度)
    std::vector<int> port_max_buffer_depth;   // 記錄各通道 Buffer 發生過的最大深度
};

#endif

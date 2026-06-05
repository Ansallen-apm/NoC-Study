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
    RoutingAlgorithm* routing_algo;

    // Input Buffers: Each port has a queue of packets
    // 輸入緩衝區：每個埠都有一個封包佇列 (動態分配大小)
    std::vector<std::queue<Packet>> input_buffers;

    // Double buffering for next cycle arrivals to avoid intra-cycle race conditions
    // 雙重緩衝區：儲存預計在下一個週期到達的封包，避免同週期競爭
    std::vector<std::queue<Packet>> next_input_buffers;

    // Track how many packets to pop from input_buffers at the end of the cycle
    // 追蹤在此週期結束時，需要從輸入緩衝區移除多少封包 (避免執行順序依賴)
    std::vector<int> pending_pops;

    // To store packets that have arrived at this destination (Local Ejection)
    // 儲存已到達此目的地的封包 (本地彈出)
    std::vector<Packet> ejected_packets;

    // Neighbor pointers and their corresponding ingress ports
    // 相鄰路由器指標與其對應的入口埠
    std::vector<Router*> neighbors;
    std::vector<int> neighbor_ingress_ports;

    Router(int id, int num_ports, int buf_size, RoutingAlgorithm* algo);
    // Connect a neighbor to a specific direction port (連接特定方向的鄰居)
    void connect(int my_port, Router* neighbor, int neighbor_ingress_port);
    // Inject a packet into the local port (注入封包至本地埠)
    bool inject_packet(Packet p);
    // Evaluate and route packets (階段一：評估與路由封包)
    void evaluate(int current_time);
    // Update buffers for next cycle (階段二：更新緩衝區狀態)
    void update();

    // Hardware Monitors (硬體監控器)
    std::vector<int> port_active_cycles;      // 記錄各通道傳輸資料的週期數 (用於計算 uRate)
    std::vector<long long> port_buffer_depth_acc; // 記錄各通道 Buffer 深度的累加值 (用於計算平均深度)
    std::vector<int> port_max_buffer_depth;   // 記錄各通道 Buffer 發生過的最大深度
};

#endif

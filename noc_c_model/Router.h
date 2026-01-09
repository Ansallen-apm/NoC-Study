#ifndef ROUTER_H
#define ROUTER_H

#include <vector>
#include <queue>
#include "Packet.h"
#include "Config.h"

// Directions (方向列舉)
enum Direction { LOCAL = 0, NORTH, EAST, SOUTH, WEST, NUM_DIRS };

class Router {
public:
    int id;
    int x, y;

    // Input Buffers: Each port has a queue of packets
    // 輸入緩衝區：每個埠都有一個封包佇列
    std::queue<Packet> input_buffers[NUM_DIRS];

    // To store packets that have arrived at this destination (Local Ejection)
    // 儲存已到達此目的地的封包 (本地彈出)
    std::vector<Packet> ejected_packets;

    // Neighbor pointers (simplified pointer based connection)
    // 相鄰路由器指標 (簡化的指標連接)
    Router* neighbors[NUM_DIRS];

    Router(int id);
    // Connect a neighbor to a specific direction (連接特定方向的鄰居)
    void connect(Direction dir, Router* neighbor);
    // Inject a packet into the local port (注入封包至本地埠)
    bool inject_packet(Packet p);
    // Run one simulation cycle (執行一個模擬週期)
    void step();

private:
    // Route packet based on ingress direction (根據入口方向路由封包)
    void route_packet(Packet p, Direction ingress_dir);
    // Compute next hop direction based on destination (根據目的地計算下一跳方向)
    Direction compute_next_hop(int dst_id);
};

#endif

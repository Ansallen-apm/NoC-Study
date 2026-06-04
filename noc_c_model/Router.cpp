#include "Router.h"
#include <iostream>

Router::Router(int _id, int num_ports, int buf_size, RoutingAlgorithm* algo)
    : id(_id), buffer_size(buf_size), num_ports(num_ports), routing_algo(algo) {

    input_buffers.resize(num_ports);
    next_input_buffers.resize(num_ports);
    pending_pops.resize(num_ports, 0);
    neighbors.resize(num_ports, nullptr);
    neighbor_ingress_ports.resize(num_ports, -1);
}

void Router::connect(int my_port, Router* neighbor, int neighbor_ingress_port) {
    neighbors[my_port] = neighbor;
    neighbor_ingress_ports[my_port] = neighbor_ingress_port;
}

bool Router::inject_packet(Packet p) {
    // 檢查本地緩衝區是否已滿 (Local port is always 0)
    if (input_buffers[0].size() < (size_t)buffer_size) {
        input_buffers[0].push(p);
        return true;
    } else {
        return false;
    }
}

void Router::evaluate(int current_time) {
    // 階段一：評估所有輸入埠的封包並決定走向 (Phase 1: Evaluate packets and determine routing)
    for (int i = 0; i < num_ports; ++i) {
        // 重置此週期的 pending_pops
        pending_pops[i] = 0;

        if (!input_buffers[i].empty()) {
            Packet p = input_buffers[i].front();

            int out_port = routing_algo->compute_next_hop(this, p.dst_id);

            bool success = false;
            if (out_port == 0) {
                // Eject (彈出封包, Port 0 is LOCAL)
                p.ejection_time = current_time;
                ejected_packets.push_back(p);
                success = true;
            } else {
                // Forward (轉發封包)
                Router* next_router = neighbors[out_port];
                int neighbor_ingress = neighbor_ingress_ports[out_port];
                if (next_router && neighbor_ingress != -1) {
                    // 檢查鄰居下一個週期的緩衝區空間 (考量目前的暫存數量與預期進入的數量)
                    // 這裡計算大小時故意不減去鄰居即將移出的數量，採取保守且同步安全的估計機制。
                    if ((next_router->input_buffers[neighbor_ingress].size() + next_router->next_input_buffers[neighbor_ingress].size()) < (size_t)next_router->buffer_size) {
                        next_router->next_input_buffers[neighbor_ingress].push(p);
                        success = true;
                    }
                }
            }

            if (success) {
                // 標記要移除，但不立刻 pop() 以避免破壞同週期的 Buffer size 同步性
                pending_pops[i] = 1;
            }
        }
    }
}

void Router::update() {
    // 階段二：將 `next_input_buffers` 轉移到 `input_buffers` (Phase 2: Update buffers)
    for (int i = 0; i < num_ports; ++i) {
        // 1. 執行真正移除封包的操作
        if (pending_pops[i] > 0) {
            input_buffers[i].pop();
        }

        // 2. 寫入新到達的封包
        while (!next_input_buffers[i].empty()) {
            input_buffers[i].push(next_input_buffers[i].front());
            next_input_buffers[i].pop();
        }
    }
}

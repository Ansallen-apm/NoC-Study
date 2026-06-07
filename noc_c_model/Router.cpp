#include "Router.h"
#include <iostream>

Router::Router(int _id, int num_ports, int num_vcs, int buf_size, RoutingAlgorithm* algo)
    : id(_id), buffer_size(buf_size), num_ports(num_ports), num_vcs(num_vcs), routing_algo(algo) {

    input_buffers.resize(num_ports, std::vector<std::queue<Flit>>(num_vcs));
    next_input_buffers.resize(num_ports, std::vector<std::queue<Flit>>(num_vcs));
    pending_pops.resize(num_ports, std::vector<int>(num_vcs, 0));

    neighbors.resize(num_ports, nullptr);
    neighbor_ingress_ports.resize(num_ports, -1);

    port_active_cycles.resize(num_ports, 0);
    port_buffer_depth_acc.resize(num_ports, 0);
    port_max_buffer_depth.resize(num_ports, 0);

    arbiter_priority.resize(num_ports, 0);
}

void Router::connect(int my_port, Router* neighbor, int neighbor_ingress_port) {
    neighbors[my_port] = neighbor;
    neighbor_ingress_ports[my_port] = neighbor_ingress_port;
}

bool Router::inject_flit(Flit f) {
    // 嘗試找到一個有空間的 VC 注入 (簡單的 VC Allocation: 第一個有空的)
    // 實務上通常固定分配給 VC 0，或是 Round Robin。這裡先找第一個有空的。
    for (int v = 0; v < num_vcs; ++v) {
        if (input_buffers[0][v].size() < (size_t)buffer_size) {
            f.vc_id = v;
            input_buffers[0][v].push(f);
            return true;
        }
    }
    return false;
}

void Router::evaluate(int current_time) {
    // 階段一：評估所有輸入埠與虛擬通道 (VC) 的 Flit 並決定走向 (Phase 1: Evaluate flits and determine routing)

    // To support Switch Allocation (Arbiter), we track if an output port has already been claimed this cycle.
    // 為了支援 Switch Allocator (仲裁器)，我們追蹤一個輸出埠是否已經在同一個週期內被佔用
    std::vector<bool> out_port_busy(num_ports, false);

    // Clear pending pops completely
    for (int i = 0; i < num_ports; ++i) {
        for (int v = 0; v < num_vcs; ++v) {
            pending_pops[i][v] = 0;
        }
    }

    // Switch Allocation (SA):
    // For each output port, we look for an input port that wants to route to it.
    // We use round-robin priority among input ports to ensure fairness.
    for (int out_port = 0; out_port < num_ports; ++out_port) {
        // Find which inputs want to go to this output port
        bool port_allocated = false;

        for (int offset = 0; offset < num_ports && !port_allocated; ++offset) {
            int in_port = (arbiter_priority[out_port] + offset) % num_ports;

            // Loop through VCs on this input port
            // VC priority could also be round-robin, but for simplicity we take the first ready VC
            for (int v = 0; v < num_vcs && !port_allocated; ++v) {
                if (!input_buffers[in_port][v].empty()) {
                    Flit f = input_buffers[in_port][v].front();

                    // Route Computation (RC)
                    int desired_out = routing_algo->compute_next_hop(this, f.dst_id);

                    if (desired_out == out_port) {
                        bool success = false;

                        if (out_port == 0) {
                            // Eject (彈出 Flit, Port 0 is LOCAL)
                            f.ejection_time = current_time;
                            ejected_flits.push_back(f);
                            success = true;
                        } else {
                            // Forward (轉發 Flit)
                            Router* next_router = neighbors[out_port];
                            int neighbor_ingress = neighbor_ingress_ports[out_port];
                            if (next_router && neighbor_ingress != -1) {
                                // 簡單的 VC Allocation:
                                // 若封包有多個 Flit，同一個 Packet 必須維持同一個 VC，避免交錯 (Interleaving)。
                                // 在這個功能性模型中，假設傳輸皆依序且維持其目前所在 VC
                                int target_vc = v;

                                // Deadlock Avoidance Dateline:
                                // 若為 Ring 拓撲且發生 wrap-around，強制切換 VC
                                // 這裡利用 id 判斷，若送往比自己 id 小且不是直接相鄰 (或是相反)，可以實作 dateline。
                                // 為求單純化並支援通用性，我們讓它保持目前 v。真正的 Dateline 實作需要配合路由演算法。

                                // Check Flow Control (Credit based equivalent)
                                if ((next_router->input_buffers[neighbor_ingress][target_vc].size() + next_router->next_input_buffers[neighbor_ingress][target_vc].size()) < (size_t)next_router->buffer_size) {
                                    f.vc_id = target_vc;
                                    next_router->next_input_buffers[neighbor_ingress][target_vc].push(f);
                                    success = true;
                                }
                            }
                        }

                        if (success) {
                            out_port_busy[out_port] = true; // Claim the crossbar
                            pending_pops[in_port][v] = 1; // Mark this flit to be popped in update phase
                            port_active_cycles[out_port]++;

                            // Update round-robin priority for this output port
                            arbiter_priority[out_port] = (in_port + 1) % num_ports;
                            port_allocated = true; // Move to the next output port
                        }
                    }
                }
            }
        }
    }
}

void Router::update() {
    // 階段二：將 `next_input_buffers` 轉移到 `input_buffers` (Phase 2: Update buffers)
    for (int i = 0; i < num_ports; ++i) {
        int total_depth_for_port = 0;

        for (int v = 0; v < num_vcs; ++v) {
            // 1. 執行真正移除封包的操作
            if (pending_pops[i][v] > 0) {
                input_buffers[i][v].pop();
            }

            // 2. 寫入新到達的封包
            while (!next_input_buffers[i][v].empty()) {
                input_buffers[i][v].push(next_input_buffers[i][v].front());
                next_input_buffers[i][v].pop();
            }

            total_depth_for_port += input_buffers[i][v].size();
        }

        // 3. 收集 Buffer Depth 統計數據 (合併所有 VC 算整個埠的負載)
        port_buffer_depth_acc[i] += total_depth_for_port;
        if (total_depth_for_port > port_max_buffer_depth[i]) {
            port_max_buffer_depth[i] = total_depth_for_port;
        }
    }
}

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

    downstream_credits.resize(num_ports, std::vector<int>(num_vcs, buffer_size));

    arbiter_priority.resize(num_ports, 0);
    vc_arbiter_priority.resize(num_ports, std::vector<int>(num_ports, 0));
}

void Router::increment_credit(int ingress_port, int vc) {
    if (ingress_port >= 0 && ingress_port < num_ports && vc >= 0 && vc < num_vcs) {
        downstream_credits[ingress_port][vc]++;
    }
}

void Router::connect(int my_port, Router* neighbor, int neighbor_ingress_port) {
    neighbors[my_port] = neighbor;
    neighbor_ingress_ports[my_port] = neighbor_ingress_port;
}

bool Router::inject_flit(Flit f) {
    // 為了保證 Dateline 的死結避免機制，新注入的封包必須強制放入 VC 0。
    // 如果 VC 0 滿了，我們必須等待，不能將其注入 VC 1 (或更高的 VC)，
    // 否則會破壞資源依賴的無環保證（cyclic dependency invariants）。
    int target_vc = 0;

    if (input_buffers[0][target_vc].size() < (size_t)buffer_size) {
        f.vc_id = target_vc;
        input_buffers[0][target_vc].push(f);
        return true;
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

            // Loop through VCs on this input port with Round-Robin priority
            for (int v_offset = 0; v_offset < num_vcs && !port_allocated; ++v_offset) {
                int v = (vc_arbiter_priority[out_port][in_port] + v_offset) % num_vcs;
                if (!input_buffers[in_port][v].empty()) {
                    Flit f = input_buffers[in_port][v].front();

                    // Route Computation (RC)
                    int desired_out = routing_algo->compute_next_hop(this, f.dst_id);

                    if (desired_out == out_port) {
                        bool success = false;

                        if (out_port == 0) {
                            // Eject (彈出 Flit, Port 0 is LOCAL)
                            f.ejection_time = current_time;
                            received_flits++;
                            if (f.type == TAIL || f.type == HEAD_TAIL) {
                                received_packets++;
                                int lat = f.ejection_time - f.creation_time;
                                total_latency += lat;
                                if (lat > max_latency) {
                                    max_latency = lat;
                                }
                            }
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
                                if (num_vcs >= 2) {
                                    bool is_dateline = false;
                                    int next_id = next_router->id;

                                    // Dimension change logic (e.g., from LOCAL/X to Y)
                                    // Only applies to Torus/Mesh which have 5 ports.
                                    if (num_ports == 5) {
                                        // If in_port is LOCAL(0), EAST(2), WEST(4) and out_port is NORTH(1), SOUTH(3)
                                        if ((in_port == 0 || in_port == 2 || in_port == 4) && (out_port == 1 || out_port == 3)) {
                                            target_vc = 0; // Reset VC when changing to Y dimension
                                        }
                                    }

                                    // Detect wraparound edges based on ID difference
                                    // A dateline link on a ring/torus dimension always goes from max to 0 or 0 to max.
                                    if (num_ports == 3) {
                                        // Special case for Ring: 1=EAST, 2=WEST. The out_port mapping is different!
                                        if (id > next_id && out_port == 1) { // EAST max->0
                                            is_dateline = true;
                                        } else if (id < next_id && out_port == 2) { // WEST 0->max
                                            is_dateline = true;
                                        }
                                    } else {
                                        // Torus / Mesh
                                        if (id > next_id && out_port == 2) { // 2=EAST, normally id < next_id. If id > next_id, it wrapped max->0
                                            is_dateline = true;
                                        } else if (id < next_id && out_port == 4) { // 4=WEST, normally id > next_id. If id < next_id, it wrapped 0->max
                                            is_dateline = true;
                                        } else if (id > next_id && out_port == 3) { // 3=SOUTH, normally id < next_id. If id > next_id, it wrapped max->0
                                            is_dateline = true;
                                        } else if (id < next_id && out_port == 1) { // 1=NORTH, normally id > next_id. If id < next_id, it wrapped 0->max
                                            is_dateline = true;
                                        }
                                    }

                                    if (is_dateline) {
                                        target_vc = 1;
                                    }
                                }

                                // Check Flow Control (Credit based equivalent)
                                if (downstream_credits[out_port][target_vc] > 0) {
                                    downstream_credits[out_port][target_vc]--; // Consume credit
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
                            vc_arbiter_priority[out_port][in_port] = (v + 1) % num_vcs;
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

                // 返回 credit 給上游
                // i 為此 Router 的輸入埠
                Router* upstream_router = neighbors[i];
                int upstream_out_port = neighbor_ingress_ports[i];
                if (upstream_router && upstream_out_port != -1) {
                    upstream_router->increment_credit(upstream_out_port, v);
                }
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

#include "Router.h"
#include <iostream>

Router::Router(int _id) : id(_id) {
    x = id % Config::MESH_WIDTH;
    y = id / Config::MESH_WIDTH;
    for (int i = 0; i < NUM_DIRS; ++i) {
        neighbors[i] = nullptr;
    }
}

void Router::connect(Direction dir, Router* neighbor) {
    neighbors[dir] = neighbor;
}

bool Router::inject_packet(Packet p) {
    // 檢查本地緩衝區是否已滿 (Check if local buffer is full)
    if (input_buffers[LOCAL].size() < Config::BUFFER_SIZE) {
        input_buffers[LOCAL].push(p);
        return true;
    } else {
        // std::cout << "Router " << id << " Local Buffer Full! Retry later." << std::endl;
        return false;
    }
}

Direction Router::compute_next_hop(int dst_id) {
    int dst_x = dst_id % Config::MESH_WIDTH;
    int dst_y = dst_id / Config::MESH_WIDTH;

    // XY Routing (XY 路由演算法)
    if (dst_x > x) return EAST;
    if (dst_x < x) return WEST;
    if (dst_y > y) return SOUTH; // Assuming Y increases downwards, 0 is top (假設 Y 向下增加，0 在頂部)
    if (dst_y < y) return NORTH;

    return LOCAL;
}

void Router::step() {
    // A simple simulation step:
    // Process one packet from each input buffer if possible.
    // In a real hardware cycle, arbitration happens.
    // Here we iterate all ports to approximate behavior.
    // 簡單的模擬步驟：如果可能，從每個輸入緩衝區處理一個封包。
    // 在真實硬體週期中，會發生仲裁。這裡我們遍歷所有埠來近似此行為。

    for (int i = 0; i < NUM_DIRS; ++i) {
        if (!input_buffers[i].empty()) {
            Packet p = input_buffers[i].front();

            Direction out_dir = compute_next_hop(p.dst_id);

            bool success = false;
            if (out_dir == LOCAL) {
                // Eject (彈出封包)
                ejected_packets.push_back(p);
                success = true;
            } else {
                // Forward (轉發封包)
                Router* next_router = neighbors[out_dir];
                if (next_router) {
                    // Reverse direction for neighbor (North's neighbor is South)
                    // 計算鄰居的入口方向 (北方的鄰居在南方)
                    Direction neighbor_ingress;
                    if (out_dir == NORTH) neighbor_ingress = SOUTH;
                    else if (out_dir == SOUTH) neighbor_ingress = NORTH;
                    else if (out_dir == EAST) neighbor_ingress = WEST;
                    else if (out_dir == WEST) neighbor_ingress = EAST;
                    else neighbor_ingress = LOCAL;

                    // 檢查鄰居緩衝區空間 (Check neighbor buffer space)
                    if (next_router->input_buffers[neighbor_ingress].size() < Config::BUFFER_SIZE) {
                        next_router->input_buffers[neighbor_ingress].push(p);
                        success = true;
                    }
                }
            }

            if (success) {
                input_buffers[i].pop();
            }
        }
    }
}

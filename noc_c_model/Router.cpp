#include "Router.h"
#include <iostream>

Router::Router(int _id, int width, int height, int buf_size) : id(_id), mesh_width(width), mesh_height(height), buffer_size(buf_size) {
    x = id % mesh_width;
    y = id / mesh_width;
    for (int i = 0; i < NUM_DIRS; ++i) {
        neighbors[i] = nullptr;
    }
}

void Router::connect(Direction dir, Router* neighbor) {
    neighbors[dir] = neighbor;
}

bool Router::inject_packet(Packet p) {
    // 檢查本地緩衝區是否已滿 (Check if local buffer is full)
    if (input_buffers[LOCAL].size() < (size_t)buffer_size) {
        input_buffers[LOCAL].push(p);
        return true;
    } else {
        // std::cout << "Router " << id << " Local Buffer Full! Retry later." << std::endl;
        return false;
    }
}

Direction Router::compute_next_hop(int dst_id) {
    int dst_x = dst_id % mesh_width;
    int dst_y = dst_id / mesh_width;

    // XY Routing (XY 路由演算法)
    if (dst_x > x) return EAST;
    if (dst_x < x) return WEST;
    if (dst_y > y) return SOUTH; // Assuming Y increases downwards, 0 is top (假設 Y 向下增加，0 在頂部)
    if (dst_y < y) return NORTH;

    return LOCAL;
}

void Router::evaluate(int current_time) {
    // 階段一：評估所有輸入埠的封包並決定走向 (Phase 1: Evaluate packets and determine routing)
    // 為了避免 Race Condition，這裡只會修改自己的 `ejected_packets` 或鄰居的 `next_input_buffers`
    for (int i = 0; i < NUM_DIRS; ++i) {
        if (!input_buffers[i].empty()) {
            Packet p = input_buffers[i].front();

            Direction out_dir = compute_next_hop(p.dst_id);

            bool success = false;
            if (out_dir == LOCAL) {
                // Eject (彈出封包)
                p.ejection_time = current_time;
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

                    // 檢查鄰居下一個週期的緩衝區空間 (考量目前的暫存數量與預期進入的數量)
                    if ((next_router->input_buffers[neighbor_ingress].size() + next_router->next_input_buffers[neighbor_ingress].size()) < (size_t)next_router->buffer_size) {
                        next_router->next_input_buffers[neighbor_ingress].push(p);
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

void Router::update() {
    // 階段二：將 `next_input_buffers` 轉移到 `input_buffers` (Phase 2: Update buffers)
    for (int i = 0; i < NUM_DIRS; ++i) {
        while (!next_input_buffers[i].empty()) {
            input_buffers[i].push(next_input_buffers[i].front());
            next_input_buffers[i].pop();
        }
    }
}

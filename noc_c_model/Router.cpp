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

    // XY Routing
    if (dst_x > x) return EAST;
    if (dst_x < x) return WEST;
    if (dst_y > y) return SOUTH; // Assuming Y increases downwards, 0 is top
    if (dst_y < y) return NORTH;

    return LOCAL;
}

void Router::step() {
    // A simple simulation step:
    // Process one packet from each input buffer if possible.
    // In a real hardware cycle, arbitration happens.
    // Here we iterate all ports to approximate behavior.

    // We need a temp storage for packets moving in this cycle to avoid instantaneous propagation
    // For simplicity in this functional model, we will move directly but be careful about order.
    // Better approach: Two-phase or simply process and push to neighbor's input.
    // Since it is a functional C model, exact cycle accuracy isn't the primary goal, but logic correctness is.

    // To avoid processing a packet that just arrived in the SAME cycle, we can't easily do that without double buffering.
    // But let's keep it simple: Just iterate.

    for (int i = 0; i < NUM_DIRS; ++i) {
        if (!input_buffers[i].empty()) {
            Packet p = input_buffers[i].front();

            Direction out_dir = compute_next_hop(p.dst_id);

            bool success = false;
            if (out_dir == LOCAL) {
                // Eject
                ejected_packets.push_back(p);
                success = true;
            } else {
                // Forward
                Router* next_router = neighbors[out_dir];
                if (next_router) {
                    // Reverse direction for neighbor (North's neighbor is South)
                    // Wait, we just need to push to the specific port of the neighbor?
                    // Usually Input buffer is associated with the port.
                    // If I send East, it enters the West port of the East neighbor.

                    Direction neighbor_ingress;
                    if (out_dir == NORTH) neighbor_ingress = SOUTH;
                    else if (out_dir == SOUTH) neighbor_ingress = NORTH;
                    else if (out_dir == EAST) neighbor_ingress = WEST;
                    else if (out_dir == WEST) neighbor_ingress = EAST;
                    else neighbor_ingress = LOCAL; // Should not happen for forwarding

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

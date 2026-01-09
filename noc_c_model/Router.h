#ifndef ROUTER_H
#define ROUTER_H

#include <vector>
#include <queue>
#include "Packet.h"
#include "Config.h"

// Directions
enum Direction { LOCAL = 0, NORTH, EAST, SOUTH, WEST, NUM_DIRS };

class Router {
public:
    int id;
    int x, y;

    // Input Buffers: Each port has a queue of packets
    std::queue<Packet> input_buffers[NUM_DIRS];

    // To store packets that have arrived at this destination (Local Ejection)
    std::vector<Packet> ejected_packets;

    // Neighbor pointers (simplified pointer based connection)
    Router* neighbors[NUM_DIRS];

    Router(int id);
    void connect(Direction dir, Router* neighbor);
    bool inject_packet(Packet p);
    void step(); // Run one cycle

private:
    void route_packet(Packet p, Direction ingress_dir);
    Direction compute_next_hop(int dst_id);
};

#endif

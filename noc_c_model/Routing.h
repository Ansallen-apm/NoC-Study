#ifndef ROUTER_ALGO_H
#define ROUTER_ALGO_H

#include "Packet.h"

// Abstract base class for routing algorithms
class RoutingAlgorithm {
public:
    virtual ~RoutingAlgorithm() = default;

    // Compute the next hop port id for a given packet currently at router_id
    virtual int compute_next_hop(int router_id, int dst_id) = 0;
};

// XY Routing (for Mesh / Torus)
class XYRouting : public RoutingAlgorithm {
private:
    int mesh_width;
    int mesh_height;
public:
    XYRouting(int width, int height) : mesh_width(width), mesh_height(height) {}

    // Assume ports: 0=LOCAL, 1=NORTH, 2=EAST, 3=SOUTH, 4=WEST
    int compute_next_hop(int router_id, int dst_id) override;
};

// Shortest Path 1D (for Ring)
class RingRouting : public RoutingAlgorithm {
private:
    int num_nodes;
public:
    RingRouting(int nodes) : num_nodes(nodes) {}

    // Assume ports: 0=LOCAL, 1=EAST, 2=WEST
    int compute_next_hop(int router_id, int dst_id) override;
};

#endif

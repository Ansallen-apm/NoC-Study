#include "Routing.h"
#include <cstdlib>
#include <algorithm>

// Enum matching original implementation for Mesh: LOCAL=0, NORTH=1, EAST=2, SOUTH=3, WEST=4
int XYRouting::compute_next_hop(int router_id, int dst_id) {
    if (router_id == dst_id) return 0; // LOCAL

    int src_x = router_id % mesh_width;
    int src_y = router_id / mesh_width;
    int dst_x = dst_id % mesh_width;
    int dst_y = dst_id / mesh_width;

    if (dst_x > src_x) return 2; // EAST
    if (dst_x < src_x) return 4; // WEST
    if (dst_y > src_y) return 3; // SOUTH
    if (dst_y < src_y) return 1; // NORTH

    return 0; // LOCAL
}

int RingRouting::compute_next_hop(int router_id, int dst_id) {
    if (router_id == dst_id) return 0; // LOCAL

    // Find shortest path direction on a ring
    // Ports: 0=LOCAL, 1=EAST (Right), 2=WEST (Left)
    int dist_right = (dst_id - router_id + num_nodes) % num_nodes;
    int dist_left = (router_id - dst_id + num_nodes) % num_nodes;

    if (dist_right <= dist_left) {
        return 1; // EAST
    } else {
        return 2; // WEST
    }
}

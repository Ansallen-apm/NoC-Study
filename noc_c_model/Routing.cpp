#include "Routing.h"
#include "Router.h"
#include <cstdlib>
#include <algorithm>

// Enum matching original implementation for Mesh: LOCAL=0, NORTH=1, EAST=2, SOUTH=3, WEST=4
int XYRouting::compute_next_hop(const Router* current_router, int dst_id) {
    int router_id = current_router->id;
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

int TorusRouting::compute_next_hop(const Router* current_router, int dst_id) {
    int router_id = current_router->id;
    if (router_id == dst_id) return 0; // LOCAL

    int src_x = router_id % mesh_width;
    int src_y = router_id / mesh_width;
    int dst_x = dst_id % mesh_width;
    int dst_y = dst_id / mesh_width;

    // Dimension Order Routing: route X first, then Y
    if (src_x != dst_x) {
        // Calculate right and left distances
        int dist_right = (dst_x - src_x + mesh_width) % mesh_width;
        int dist_left = (src_x - dst_x + mesh_width) % mesh_width;
        if (dist_right <= dist_left) {
            return 2; // EAST
        } else {
            return 4; // WEST
        }
    }

    if (src_y != dst_y) {
        // Calculate down and up distances
        int dist_down = (dst_y - src_y + mesh_height) % mesh_height;
        int dist_up = (src_y - dst_y + mesh_height) % mesh_height;
        if (dist_down <= dist_up) {
            return 3; // SOUTH
        } else {
            return 1; // NORTH
        }
    }

    return 0; // LOCAL
}

int RingRouting::compute_next_hop(const Router* current_router, int dst_id) {
    int router_id = current_router->id;
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

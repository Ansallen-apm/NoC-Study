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

    int dist_x = dst_x - src_x;
    int dist_y = dst_y - src_y;

    // Address wrap-around for Torus networks conceptually in XY routing (shortest path)
    if (std::abs(dist_x) > mesh_width / 2) {
        dist_x = dist_x > 0 ? dist_x - mesh_width : dist_x + mesh_width;
    }
    if (std::abs(dist_y) > mesh_height / 2) {
        dist_y = dist_y > 0 ? dist_y - mesh_height : dist_y + mesh_height;
    }

    if (dist_x > 0) return 2; // EAST
    if (dist_x < 0) return 4; // WEST
    if (dist_y > 0) return 3; // SOUTH
    if (dist_y < 0) return 1; // NORTH

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

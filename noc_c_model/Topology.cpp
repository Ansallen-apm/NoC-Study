#include "Topology.h"
#include "Router.h"

// Mesh Mapping: 1=NORTH, 2=EAST, 3=SOUTH, 4=WEST
void MeshTopology::build_network(std::vector<Router*>& routers) {
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            int id = y * width + x;
            Router* r = routers[id];

            // North
            if (y > 0) r->connect(1, routers[(y - 1) * width + x], 3); // Tell North neighbor our port to it is 1, and its ingress from us is 3 (South)
            // South
            if (y < height - 1) r->connect(3, routers[(y + 1) * width + x], 1);
            // West
            if (x > 0) r->connect(4, routers[y * width + (x - 1)], 2);
            // East
            if (x < width - 1) r->connect(2, routers[y * width + (x + 1)], 4);
        }
    }
}

// Torus Mapping: 1=NORTH, 2=EAST, 3=SOUTH, 4=WEST
void TorusTopology::build_network(std::vector<Router*>& routers) {
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            int id = y * width + x;
            Router* r = routers[id];

            // North
            int n_y = (y - 1 + height) % height;
            r->connect(1, routers[n_y * width + x], 3);

            // South
            int s_y = (y + 1) % height;
            r->connect(3, routers[s_y * width + x], 1);

            // West
            int w_x = (x - 1 + width) % width;
            r->connect(4, routers[y * width + w_x], 2);

            // East
            int e_x = (x + 1) % width;
            r->connect(2, routers[y * width + e_x], 4);
        }
    }
}

// Ring Mapping: 1=EAST(Right), 2=WEST(Left)
void RingTopology::build_network(std::vector<Router*>& routers) {
    for (int i = 0; i < num_nodes; ++i) {
        Router* r = routers[i];

        int east_id = (i + 1) % num_nodes;
        int west_id = (i - 1 + num_nodes) % num_nodes;

        r->connect(1, routers[east_id], 2); // My East (1) connects to neighbor's West (2)
        r->connect(2, routers[west_id], 1); // My West (2) connects to neighbor's East (1)
    }
}

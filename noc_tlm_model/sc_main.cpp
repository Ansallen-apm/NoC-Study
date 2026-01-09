#include <systemc>
#include <vector>
#include "Router_TLM.h"

using namespace sc_core;

int sc_main(int argc, char* argv[]) {
    // 2x2 Mesh Configuration
    const int MESH_WIDTH = 2;
    const int MESH_HEIGHT = 2;

    std::vector<Router_TLM*> routers;

    // Create Routers
    for (int i = 0; i < MESH_WIDTH * MESH_HEIGHT; ++i) {
        char name[10];
        sprintf(name, "r%d", i);
        routers.push_back(new Router_TLM(name, i));
    }

    // Connect Mesh
    for (int y = 0; y < MESH_HEIGHT; ++y) {
        for (int x = 0; x < MESH_WIDTH; ++x) {
            int id = y * MESH_WIDTH + x;
            Router_TLM* r = routers[id];

            // North (Port 1) <-> South (Port 3) of neighbor
            if (y > 0) {
                int neighbor_id = (y - 1) * MESH_WIDTH + x;
                Router_TLM* n = routers[neighbor_id];
                // Bind Initiator 1 (North) to Target 3 (South)
                r->initiator_socket[1].bind(n->target_socket[3]);
                // Bind Initiator 3 (South) to Target 1 (North)
                n->initiator_socket[3].bind(r->target_socket[1]);
            }

            // West (Port 4) <-> East (Port 2) of neighbor
            if (x > 0) {
                int neighbor_id = y * MESH_WIDTH + (x - 1);
                Router_TLM* n = routers[neighbor_id];
                // Bind Initiator 4 (West) to Target 2 (East)
                r->initiator_socket[4].bind(n->target_socket[2]);
                // Bind Initiator 2 (East) to Target 4 (West)
                n->initiator_socket[2].bind(r->target_socket[4]);
            }
        }
    }

    sc_start();

    // Cleanup
    for(auto r : routers) delete r;

    return 0;
}

#include <systemc>
#include <vector>
#include "Router_TLM.h"

using namespace sc_core;

int sc_main(int argc, char* argv[]) {
    // 2x2 Mesh Configuration (2x2 網格配置)
    const int MESH_WIDTH = 2;
    const int MESH_HEIGHT = 2;

    std::vector<Router_TLM*> routers;

    // Create Routers (建立路由器)
    for (int i = 0; i < MESH_WIDTH * MESH_HEIGHT; ++i) {
        char name[10];
        sprintf(name, "r%d", i);
        routers.push_back(new Router_TLM(name, i));
    }

    // Connect Mesh (連接網格)
    for (int y = 0; y < MESH_HEIGHT; ++y) {
        for (int x = 0; x < MESH_WIDTH; ++x) {
            int id = y * MESH_WIDTH + x;
            Router_TLM* r = routers[id];

            // North (Port 1) <-> South (Port 3) of neighbor
            // 北 (埠 1) <-> 鄰居的南 (埠 3)
            if (y > 0) {
                int neighbor_id = (y - 1) * MESH_WIDTH + x;
                Router_TLM* n = routers[neighbor_id];
                // Bind Initiator 1 (North) to Target 3 (South)
                // 綁定啟動器 1 (北) 到目標 3 (南)
                r->initiator_socket[1].bind(n->target_socket[3]);
                // Bind Initiator 3 (South) to Target 1 (North)
                // 綁定啟動器 3 (南) 到目標 1 (北)
                n->initiator_socket[3].bind(r->target_socket[1]);
            }

            // West (Port 4) <-> East (Port 2) of neighbor
            // 西 (埠 4) <-> 鄰居的東 (埠 2)
            if (x > 0) {
                int neighbor_id = y * MESH_WIDTH + (x - 1);
                Router_TLM* n = routers[neighbor_id];
                // Bind Initiator 4 (West) to Target 2 (East)
                // 綁定啟動器 4 (西) 到目標 2 (東)
                r->initiator_socket[4].bind(n->target_socket[2]);
                // Bind Initiator 2 (East) to Target 4 (West)
                // 綁定啟動器 2 (東) 到目標 4 (西)
                n->initiator_socket[2].bind(r->target_socket[4]);
            }
        }
    }

    sc_start();

    // Cleanup (清理)
    for(auto r : routers) delete r;

    return 0;
}

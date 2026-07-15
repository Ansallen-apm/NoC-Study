#include <gtest/gtest.h>
#include "../Topology.h"
#include "../Router.h"
#include "../Routing.h"

// Helper function to create and build a topology
template <typename T>
void test_topology_wiring(T& topo, int num_nodes) {
    std::vector<std::unique_ptr<Router>> routers;
    std::vector<Router*> raw_routers;

    // We can use XYRouting for all just to instantiate the router, it doesn't affect topology wiring
    XYRouting dummy_routing(2, 2);

    for (int i = 0; i < num_nodes; ++i) {
        routers.push_back(std::unique_ptr<Router>(new Router(i, topo.get_max_ports(), 2, 4, &dummy_routing)));
        raw_routers.push_back(routers.back().get());
    }

    topo.build_network(raw_routers);

    // Common port mappings:
    // Mesh/Torus: 1=NORTH, 2=EAST, 3=SOUTH, 4=WEST
    // Ring: 1=EAST, 2=WEST
}

TEST(TopologyTest, Mesh2x2) {
    MeshTopology topo(2, 2);
    std::vector<std::unique_ptr<Router>> routers;
    std::vector<Router*> raw_routers;
    XYRouting dummy_routing(2, 2);

    for (int i = 0; i < 4; ++i) {
        routers.push_back(std::unique_ptr<Router>(new Router(i, topo.get_max_ports(), 2, 4, &dummy_routing)));
        raw_routers.push_back(routers.back().get());
    }
    topo.build_network(raw_routers);

    // Node 0 (0,0): East=1, South=2
    EXPECT_EQ(routers[0]->neighbors[2], routers[1].get()); // East
    EXPECT_EQ(routers[0]->neighbor_ingress_ports[2], 4); // Ingress to 1's West

    EXPECT_EQ(routers[0]->neighbors[3], routers[2].get()); // South
    EXPECT_EQ(routers[0]->neighbor_ingress_ports[3], 1); // Ingress to 2's North

    EXPECT_EQ(routers[0]->neighbors[1], nullptr); // North
    EXPECT_EQ(routers[0]->neighbors[4], nullptr); // West

    // Node 3 (1,1): North=1, West=2
    EXPECT_EQ(routers[3]->neighbors[1], routers[1].get()); // North
    EXPECT_EQ(routers[3]->neighbor_ingress_ports[1], 3); // Ingress to 1's South

    EXPECT_EQ(routers[3]->neighbors[4], routers[2].get()); // West
    EXPECT_EQ(routers[3]->neighbor_ingress_ports[4], 2); // Ingress to 2's East
}

TEST(TopologyTest, Torus3x3) {
    TorusTopology topo(3, 3);
    std::vector<std::unique_ptr<Router>> routers;
    std::vector<Router*> raw_routers;
    XYRouting dummy_routing(3, 3);

    for (int i = 0; i < 9; ++i) {
        routers.push_back(std::unique_ptr<Router>(new Router(i, topo.get_max_ports(), 2, 4, &dummy_routing)));
        raw_routers.push_back(routers.back().get());
    }
    topo.build_network(raw_routers);

    // Node 0 (0,0): Wraparounds to North=6, West=2
    // Direct: East=1, South=3
    EXPECT_EQ(routers[0]->neighbors[1], routers[6].get()); // North (Wrap)
    EXPECT_EQ(routers[0]->neighbor_ingress_ports[1], 3); // South of 6

    EXPECT_EQ(routers[0]->neighbors[4], routers[2].get()); // West (Wrap)
    EXPECT_EQ(routers[0]->neighbor_ingress_ports[4], 2); // East of 2

    EXPECT_EQ(routers[0]->neighbors[2], routers[1].get()); // East
    EXPECT_EQ(routers[0]->neighbor_ingress_ports[2], 4); // West of 1

    EXPECT_EQ(routers[0]->neighbors[3], routers[3].get()); // South
    EXPECT_EQ(routers[0]->neighbor_ingress_ports[3], 1); // North of 3

    // Node 8 (2,2): Wraparounds to South=2, East=6
    // Direct: North=5, West=7
    EXPECT_EQ(routers[8]->neighbors[3], routers[2].get()); // South (Wrap)
    EXPECT_EQ(routers[8]->neighbor_ingress_ports[3], 1); // North of 2

    EXPECT_EQ(routers[8]->neighbors[2], routers[6].get()); // East (Wrap)
    EXPECT_EQ(routers[8]->neighbor_ingress_ports[2], 4); // West of 6
}

TEST(TopologyTest, Ring5) {
    RingTopology topo(5);
    std::vector<std::unique_ptr<Router>> routers;
    std::vector<Router*> raw_routers;
    XYRouting dummy_routing(2, 2);

    for (int i = 0; i < 5; ++i) {
        routers.push_back(std::unique_ptr<Router>(new Router(i, topo.get_max_ports(), 2, 4, &dummy_routing)));
        raw_routers.push_back(routers.back().get());
    }
    topo.build_network(raw_routers);

    // Ring Mapping: 1=EAST(Right), 2=WEST(Left)
    // Node 0: East=1, West=4 (Wrap)
    EXPECT_EQ(routers[0]->neighbors[1], routers[1].get()); // East
    EXPECT_EQ(routers[0]->neighbor_ingress_ports[1], 2); // West of 1

    EXPECT_EQ(routers[0]->neighbors[2], routers[4].get()); // West (Wrap)
    EXPECT_EQ(routers[0]->neighbor_ingress_ports[2], 1); // East of 4

    // Node 4: East=0 (Wrap), West=3
    EXPECT_EQ(routers[4]->neighbors[1], routers[0].get()); // East (Wrap)
    EXPECT_EQ(routers[4]->neighbor_ingress_ports[1], 2); // West of 0

    EXPECT_EQ(routers[4]->neighbors[2], routers[3].get()); // West
    EXPECT_EQ(routers[4]->neighbor_ingress_ports[2], 1); // East of 3
}

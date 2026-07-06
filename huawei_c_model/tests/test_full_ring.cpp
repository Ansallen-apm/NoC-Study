#include <gtest/gtest.h>
#include "simulator.hpp"
#include "ring.hpp"
#include "cross_station.hpp"

TEST(Phase2Test, FullRingShortestPath) {
    Simulator sim;
    sim.config.topology = "test_full_ring";
    sim.init_topology();

    ASSERT_EQ(sim.rings.size(), 1);
    ASSERT_EQ(sim.stations.size(), 8);

    // Node 0 -> Node 7: CCW distance = 1, CW distance = 7
    // Direction should be CCW
    Direction dir = sim.stations[0]->choose_direction(0, 7, 8);
    EXPECT_EQ(dir, Direction::CCW);

    Flit f;
    f.id = 1;
    f.src_node = 0;
    f.dst_node = 7;
    f.dir = dir;

    sim.stations[0]->node_if[0].inject_q.push(f);

    // Cycle 1: flit is injected at station 0 CCW port, Ring tock moves it to CCW slot 7 (which is index 7)
    sim.run(1);

    // Cycle 2: flit at slot 7 is processed by station 7, ejected
    sim.run(1);

    EXPECT_FALSE(sim.stations[7]->node_if[0].eject_q.q.empty());
    EXPECT_EQ(sim.stations[7]->node_if[0].eject_q.q.front().id, 1);
}

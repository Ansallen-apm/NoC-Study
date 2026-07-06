#include <gtest/gtest.h>
#include "simulator.hpp"
#include "ring.hpp"
#include "cross_station.hpp"

TEST(Phase1Test, SingleHalfRingLatency) {
    Simulator sim;
    sim.config.topology = "test_single_ring";
    sim.init_topology();

    ASSERT_EQ(sim.rings.size(), 1);
    ASSERT_EQ(sim.stations.size(), 4);

    // Inject flit at station 0, destined for station 2
    Flit f;
    f.id = 1;
    f.src_node = 0;
    f.dst_node = 2;
    f.dir = Direction::CW;

    sim.stations[0]->node_if[0].inject_q.push(f);

    // Run cycle 1: Tick injects flit at station 0, moves to next_cw_out[0], then Ring tock moves it to curr_cw_slots[1]
    sim.run(1);
    EXPECT_TRUE(sim.rings[0]->curr_cw_slots[1].occupied);
    EXPECT_EQ(sim.rings[0]->curr_cw_slots[1].flit.id, 1);

    // Run cycle 2: Flit at curr_cw_slots[1] passes station 1 next_cw_out[1], Ring tock moves it to curr_cw_slots[2]
    sim.run(1);
    EXPECT_TRUE(sim.rings[0]->curr_cw_slots[2].occupied);
    EXPECT_EQ(sim.rings[0]->curr_cw_slots[2].flit.id, 1);

    // Run cycle 3: Flit at curr_cw_slots[2] is processed by station 2, ejected immediately into queue during tick.
    sim.run(1);
    // Ejected to node 2
    EXPECT_TRUE(sim.stations[2]->node_if[0].eject_q.has_space());
    EXPECT_FALSE(sim.stations[2]->node_if[0].eject_q.q.empty());
    EXPECT_EQ(sim.stations[2]->node_if[0].eject_q.q.front().id, 1);
}

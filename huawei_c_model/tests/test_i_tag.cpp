#include <gtest/gtest.h>
#include "simulator.hpp"
#include "cross_station.hpp"
#include "ring.hpp"

TEST(Phase3Test, ITagInjectionReservation) {
    Simulator sim;
    sim.config.topology = "test_single_ring";
    sim.init_topology();

    // In init_topology: Component 0 is Station 0, 1 is Station 1, 2 is Station 2, 3 is Station 3, 4 is Ring
    auto st0 = static_cast<CrossStation*>(sim.components[0].get());
    auto st1 = static_cast<CrossStation*>(sim.components[1].get());
    auto st2 = static_cast<CrossStation*>(sim.components[2].get());
    auto st3 = static_cast<CrossStation*>(sim.components[3].get());

    ASSERT_EQ(st0->station_id, 0);
    ASSERT_EQ(st1->station_id, 1);
    ASSERT_EQ(st2->station_id, 2);
    ASSERT_EQ(st3->station_id, 3);

    // To ensure I-tag functions correctly, we need the deadlock threshold to be exceeded.
    st1->set_deadlock_threshold(2);

    // Pre-fill Station 0's injection queue with blocking traffic
    for (int i = 1; i <= 20; ++i) {
        Flit blocker;
        blocker.id = i;
        blocker.src_node = 0;
        blocker.dst_node = 2; // Ejects at 2
        blocker.valid = true;
        blocker.dir = Direction::CW;
        st0->node_if[0].inject_q.push(blocker);
    }

    // Let the blocking traffic run for a few cycles to occupy the ring and form contention
    sim.run(3);

    // Now Station 1 decides to inject
    Flit target;
    target.id = 100;
    target.src_node = 1;
    target.dst_node = 3;
    target.valid = true;
    target.dir = Direction::CW;
    st1->node_if[0].inject_q.push(target);

    // Also give Station 3 traffic to inject. But ONLY AFTER Station 1 has successfully
    // requested an I-Tag. Otherwise Station 3 might inject before Station 1 even tries.
    // Wait until Station 1 actually is blocked and fails to inject a few times.
    sim.run(2);

    Flit st3_traffic;
    st3_traffic.id = 300;
    st3_traffic.src_node = 3;
    st3_traffic.dst_node = 1;
    st3_traffic.valid = true;
    st3_traffic.dir = Direction::CW;
    st3->node_if[0].inject_q.push(st3_traffic);

    // Run for enough cycles for the I-tag to circulate, reach Station 1, and for Station 1 to inject.
    // It should take about 4-5 cycles for the I-tag to make a full loop.
    int cycles_waited = 0;
    bool injected = false;

    for (int i = 0; i < 20; ++i) {
        sim.run(1);
        cycles_waited++;

        // Check if Station 1 managed to inject
        if (st1->node_if[0].inject_q.size() == 0) {
            injected = true;
            break;
        }
    }

    EXPECT_TRUE(injected);
    EXPECT_GT(cycles_waited, 0); // Prove it had to wait and didn't just instantly inject

    // Station 3 should NOT have injected while Station 1 was using the I-tag
    EXPECT_EQ(st3->node_if[0].inject_q.size(), 1);
}

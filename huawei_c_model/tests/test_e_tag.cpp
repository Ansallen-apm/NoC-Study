#include <gtest/gtest.h>
#include "cross_station.hpp"
#include "ring.hpp"
#include <iostream>

TEST(Phase3Test, ETagEjectionDeflection) {
    Ring ring(0, 4, false);
    CrossStation station(0, &ring);

    // Shrink buffer to capacity=1
    station.node_if[0].eject_q.capacity = 1;
    station.node_if[0].eject_q.max_reservations = 1;
    station.node_if[1].eject_q.capacity = 1; // Need to limit both, otherwise it will eject to port 1
    station.node_if[1].eject_q.max_reservations = 0;

    // Pre-fill the eject queues to force the incoming flit to deflect
    Flit blocker1; blocker1.id = 1; blocker1.valid = true;
    station.node_if[0].eject_q.push(blocker1);

    Flit blocker2; blocker2.id = 99; blocker2.valid = true;
    station.node_if[1].eject_q.push(blocker2);

    // Flit arrives at station 0, wants to eject at node 0
    Flit incoming;
    incoming.id = 2;
    incoming.dst_node = 0;
    incoming.valid = true;
    incoming.deflect_count = 0;

    ring.curr_cw_slots[0].occupied = true;
    ring.curr_cw_slots[0].flit = incoming;
    ring.curr_cw_slots[0].e_tag = false;

    // Cycle 1: It should fail to eject and must DEFLECT, claiming E-tag reservation
    station.tick();

    EXPECT_TRUE(ring.next_cw_slots[0].occupied); // Deflected
    EXPECT_TRUE(ring.next_cw_slots[0].e_tag); // E-tag acquired
    EXPECT_EQ(ring.next_cw_slots[0].flit.id, 2);
    EXPECT_EQ(ring.next_cw_slots[0].flit.deflect_count, 1);
    EXPECT_TRUE(station.node_if[0].eject_q.is_reserved_for(2));

    // Empty the queue so it has space now
    station.node_if[0].eject_q.pop_oldest();

    // Re-inject the deflected flit (with E-tag) back to station 0
    ring.curr_cw_slots[0] = ring.next_cw_slots[0];
    // clear output slot for test
    ring.next_cw_slots[0].occupied = false;
    ring.next_cw_slots[0].e_tag = false;

    station.tick();

    // Cycle 2: It should successfully eject because it had space and reservation
    EXPECT_FALSE(ring.next_cw_slots[0].occupied);
    EXPECT_FALSE(ring.next_cw_slots[0].e_tag); // e-tag consumed

    // Verify it is in the eject queue
    EXPECT_EQ(station.node_if[0].eject_q.size(), 1);
    EXPECT_EQ(station.node_if[0].eject_q.q.front().id, 2);
}

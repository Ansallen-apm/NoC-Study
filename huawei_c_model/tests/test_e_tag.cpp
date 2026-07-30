#include <gtest/gtest.h>
#include "cross_station.hpp"
#include "ring.hpp"
#include <iostream>

TEST(Phase3Test, ETagEjectionDeflection) {
    Ring ring(0, 4, false);
    CrossStation station(0, &ring);

    station.node_if[0].eject_q.capacity = 2;
    station.node_if[0].eject_q.max_reservations = 1;
    station.node_if[1].eject_q.capacity = 1;
    station.node_if[1].eject_q.max_reservations = 0;

    Flit blocker1; blocker1.id = 1; blocker1.valid = true;
    station.node_if[0].eject_q.q.push_back(blocker1);

    // Explicitly reserve for flit 2
    station.node_if[0].eject_q.reserve(2);

    Flit blocker2; blocker2.id = 99; blocker2.valid = true;
    station.node_if[1].eject_q.q.push_back(blocker2);

    // Flit 3 (no tag) arrives at station 0, wants to eject at node 0
    Flit flit_no_tag;
    flit_no_tag.id = 3;
    flit_no_tag.dst_node = 0;
    flit_no_tag.valid = true;
    flit_no_tag.deflect_count = 0;

    ring.curr_cw_slots[0].occupied = true;
    ring.curr_cw_slots[0].flit = flit_no_tag;
    ring.curr_cw_slots[0].e_tag = false;

    // Cycle 1: It should fail to eject because size=1 + reserved=1 == capacity=2
    // So it deflects!
    station.tick();

    EXPECT_TRUE(ring.next_cw_slots[0].occupied); // Deflected
    EXPECT_EQ(ring.next_cw_slots[0].flit.id, 3);
    EXPECT_EQ(ring.next_cw_slots[0].flit.deflect_count, 1);

    // Now Flit 2 (WITH tag) arrives
    Flit flit_with_tag;
    flit_with_tag.id = 2;
    flit_with_tag.dst_node = 0;
    flit_with_tag.valid = true;
    flit_with_tag.deflect_count = 1;

    ring.curr_cw_slots[0].occupied = true;
    ring.curr_cw_slots[0].flit = flit_with_tag;
    ring.curr_cw_slots[0].e_tag = true;
    ring.curr_cw_slots[0].e_tag_flit_id = 2;

    // clear output
    ring.next_cw_slots[0].occupied = false;
    ring.next_cw_slots[0].e_tag = false;

    station.tick();

    // Cycle 2: It should successfully eject because it HAD the reservation, and actual size = 1 < capacity = 2!
    EXPECT_FALSE(ring.next_cw_slots[0].occupied);

    // Verify it is in the eject queue
    EXPECT_EQ(station.node_if[0].eject_q.size(), 2);
    EXPECT_EQ(station.node_if[0].eject_q.q.back().id, 2);
}

#include <gtest/gtest.h>
#include "rbrg_l1.hpp"
#include "ring.hpp"
#include "router.hpp"

class Phase4Test : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
};

TEST_F(Phase4Test, RBRGL1RingChange) {
    Ring ringA(0, 4, false);
    Ring ringB(1, 4, false);

    RBRGL1Config config;
    config.latency_cycles = 2;
    config.queue_depth = 4;

    std::shared_ptr<Router> router = std::make_shared<MultiRingRouter>();
    RBRG_L1 bridge(0, 1, 1, 2, config, router);

    bridge.set_local_ring(&ringA);
    bridge.set_remote_ring(&ringB);

    // Initial state: inject at Station 0
    Flit f;
    f.id = 1;
    f.valid = true;
    f.src_ring = 0;
    f.src_node = 0;
    f.dst_ring = 1;
    f.dst_node = 3;

    // Cross station 0 writes to next_cw_slots[0]
    ringA.next_cw_slots[0].flit = f;
    ringA.next_cw_slots[0].occupied = true;
    ringA.tock(); // Moves from next_cw_slots[0] to curr_cw_slots[1]

    bool flit_transferred = false;
    int flit_arrival_cycle = -1;

    for (int cycle = 1; cycle <= 10; ++cycle) {
        // Mocking the cross stations pass-through logic for both rings
        // In real simulation, cross stations would copy curr to next.
        for (int i=0; i<4; i++) {
            ringA.next_cw_slots[i] = ringA.curr_cw_slots[i];
            ringB.next_cw_slots[i] = ringB.curr_cw_slots[i];
        }

        // Bridge intercepts
        bridge.tick();

        ringA.tock();
        ringB.tock();
        bridge.tock();

        // Check if flit arrived in Ring B at the target inject station
        // In this test, Bridge injects at Station 2. It writes to ringB.next_cw_slots[2] in tick().
        // After ringB.tock(), it will be at curr_cw_slots[3].
        if (ringB.curr_cw_slots[3].occupied && ringB.curr_cw_slots[3].flit.id == 1) {
            flit_transferred = true;
            flit_arrival_cycle = cycle;
            break;
        }
    }

    EXPECT_TRUE(flit_transferred);
    EXPECT_GT(flit_arrival_cycle, 1);
}

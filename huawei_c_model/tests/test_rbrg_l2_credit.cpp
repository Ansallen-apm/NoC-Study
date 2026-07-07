#include <gtest/gtest.h>
#include "rbrg_l2.hpp"
#include "ring.hpp"
#include "router.hpp"

class Phase5Test : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
};

TEST_F(Phase5Test, RBRGL2CreditControl) {
    Ring ringA(0, 4, true);
    Ring ringB(10, 4, true);

    BridgeConfig b_config;
    b_config.d2d_latency_cycles = 2; // short D2D

    // Very small queues to test credit backpressure
    int queue_depth = 1;
    int credit_depth = 1;

    std::shared_ptr<Router> router = std::make_shared<MultiRingRouter>();
    RBRG_L2 bridge(0, 1, 10, 2, b_config, queue_depth, credit_depth, router);
    bridge.set_local_ring(&ringA);
    bridge.set_remote_ring(&ringB);

    // Block ring B ejection
    Flit blocker;
    blocker.id = 99;
    blocker.valid = true;
    ringB.curr_cw_slots[2].flit = blocker;
    ringB.curr_cw_slots[2].occupied = true;
    ringB.next_cw_slots[2].flit = blocker;
    ringB.next_cw_slots[2].occupied = true;

    // Inject multiple flits
    for (int cycle = 1; cycle <= 15; ++cycle) {
        if (cycle <= 5) {
            Flit f;
            f.id = cycle;
            f.valid = true;
            f.src_ring = 0;
            f.dst_ring = 10;

            ringA.curr_cw_slots[1].flit = f;
            ringA.curr_cw_slots[1].occupied = true;
        } else {
            ringA.curr_cw_slots[1].occupied = false;
        }

        bridge.tick();

        // Keep blocker
        ringB.next_cw_slots[2].flit = blocker;
        ringB.next_cw_slots[2].occupied = true;

        bridge.tock();
    }

    EXPECT_LE(bridge.get_remote_rx_queue_size(), 1);
    EXPECT_LE(bridge.get_local_rx_queue_size(), 1);
}

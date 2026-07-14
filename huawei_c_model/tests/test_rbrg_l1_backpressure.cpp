#include <gtest/gtest.h>
#include "rbrg_l1.hpp"
#include "ring.hpp"
#include "router.hpp"

// Re-declare Phase4Test fixture here for this file
class Phase4Test : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
};

TEST_F(Phase4Test, RBRGL1Backpressure) {
    Ring ringA(0, 4, false);
    Ring ringB(1, 4, false);

    RBRGL1Config config;
    config.latency_cycles = 2;
    config.queue_depth = 1; // Small queue to force backpressure

    std::shared_ptr<Router> router = std::make_shared<MultiRingRouter>();
    RBRG_L1 bridge(0, 1, 1, 2, config, router);

    bridge.set_local_ring(&ringA);
    bridge.set_remote_ring(&ringB);

    // Keep ringB occupied so bridge egress cannot inject
    Flit blocker;
    blocker.id = 99;
    blocker.valid = true;
    ringB.curr_cw_slots[2].flit = blocker;
    ringB.curr_cw_slots[2].occupied = true;
    ringB.next_cw_slots[2].flit = blocker;
    ringB.next_cw_slots[2].occupied = true;


    // Inject multiple flits into Ring A
    for (int cycle = 1; cycle <= 10; ++cycle) {
        if (cycle <= 4) {
            Flit f;
            f.id = cycle;
            f.valid = true;
            f.src_ring = 0;
            f.dst_ring = 1;

            ringA.next_cw_slots[1].flit = f;
            ringA.next_cw_slots[1].occupied = true;
        } else {
            ringA.next_cw_slots[1].occupied = false;
        }

        bridge.tick();

        // Keep blocker in place
        ringB.next_cw_slots[2].flit = blocker;
        ringB.next_cw_slots[2].occupied = true;

        bridge.tock();

    }

    // Check queues and pipelines
    EXPECT_EQ(bridge.egress_queue.size(), 1);
    EXPECT_TRUE(bridge.pipeline_regs_curr[0].valid);
    EXPECT_TRUE(bridge.pipeline_regs_curr[1].valid);

}

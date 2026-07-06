#include <gtest/gtest.h>
#include "rbrg_l2.hpp"
#include "ring.hpp"
#include "router.hpp"

class Phase5Test : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
};

TEST_F(Phase5Test, RBRGL2DieToDieTransfer) {
    // 1. Setup two full rings representing two Dies
    Ring ringA(0, 4, true); // Ring 0 (CCD0)
    Ring ringB(10, 4, true); // Ring 10 (IOD0)

    // 2. Setup Config
    BridgeConfig b_config;
    b_config.type = "RBRG_L2";
    b_config.local_ring = 0;
    b_config.remote_ring = 10;
    b_config.local_station = 1;
    b_config.remote_station = 2;
    b_config.d2d_latency_cycles = 4;

    // We assume default buffer depths for test
    int queue_depth = 4;
    int credit_depth = 4;

    // 3. Create RBRG-L2 and D2D link
    std::shared_ptr<Router> router = std::make_shared<MultiRingRouter>();

    // Two halves of the bridge for accurate modeling, or a single component abstracting both?
    // According to Huawei_CA_model_plan.md, RBRG-L2 handles inter-die bridging.
    // It's usually symmetric: one RBRG-L2 agent on Die 0, one on Die 1, connected by a D2D link.
    // Let's model a monolithic RBRG_L2 component for now that contains both Die interfaces
    // and the D2D latency pipeline internally to simplify integration, OR
    // model it properly as two nodes and a link.
    // Plan states: "Inter-die latency = source ring latency + RBRG-L2 latency + D2D latency + destination ring latency"

    // We'll design RBRG_L2 class to bridge two rings, internally containing the D2D pipeline.
    RBRG_L2 bridge(0, 1, 10, 2, b_config, queue_depth, credit_depth, router);
    bridge.set_local_ring(&ringA);
    bridge.set_remote_ring(&ringB);

    // 4. Inject a flit into Ring A at Station 0
    Flit f;
    f.id = 1;
    f.valid = true;
    f.src_ring = 0;
    f.src_node = 0;
    f.dst_ring = 10;
    f.dst_node = 3;

    ringA.next_cw_slots[0].flit = f;
    ringA.next_cw_slots[0].occupied = true;
    ringA.tock();

    // 5. Run simulation
    bool flit_transferred = false;
    int flit_arrival_cycle = -1;

    for (int cycle = 1; cycle <= 20; ++cycle) {
        // Rings advance
        for (int i=0; i<4; i++) {
            ringA.next_cw_slots[i] = ringA.curr_cw_slots[i];
            ringA.next_ccw_slots[i] = ringA.curr_ccw_slots[i];
            ringB.next_cw_slots[i] = ringB.curr_cw_slots[i];
            ringB.next_ccw_slots[i] = ringB.curr_ccw_slots[i];
        }

        bridge.tick();

        ringA.tock();
        ringB.tock();
        bridge.tock();

        if (ringB.curr_cw_slots[3].occupied && ringB.curr_cw_slots[3].flit.id == 1) {
            flit_transferred = true;
            flit_arrival_cycle = cycle;
            break;
        }
    }

    EXPECT_TRUE(flit_transferred);
    // Cycle 1: Station 0 to Station 1 (Ring A). Ejected into Bridge.
    // Bridge latency ~1-2 cycles + D2D Latency (4 cycles) + Inject latency.
    // Should arrive much later than RBRG-L1.
    EXPECT_GT(flit_arrival_cycle, 6);
}

#include <gtest/gtest.h>
#include "cross_station.hpp"
#include "ring.hpp"
#include "swap_sink.hpp"
#include "rbrg_l2.hpp"
#include "router.hpp"

// Mock SwapSink to isolate CrossStation testing
class MockSwapSink : public SwapSink {
public:
    int accepted_swaps = 0;
    bool block_swaps = false;

    bool can_accept_swap() const override {
        return !block_swaps;
    }

    void accept_swap(const Flit& f) override {
        accepted_swaps++;
    }
};

TEST(Phase6Test, DRMDetectionAndSwap) {
    Ring ring(0, 4, false);
    CrossStation station(0, &ring);
    station.node_if[0].eject_q.capacity = 1;
    station.node_if[0].inject_q.capacity = 1;

    DeadlockConfig dl_cfg;
    dl_cfg.threshold_cycles = 5; // Small threshold for quick test
    station.set_deadlock_threshold(dl_cfg.threshold_cycles);

    MockSwapSink mock_sink;
    station.set_swap_sink(&mock_sink);

    // 1. Fill the EjectQueue
    Flit eject_flit;
    eject_flit.valid = true;
    eject_flit.dst_ring = 0;
    eject_flit.dst_node = 0;

    // We bypass tick to fill the queue for testing
    station.node_if[0].eject_q.push(eject_flit);

    // 2. Put a flit in InjectQueue (wants to inject)
    Flit inject_flit;
    inject_flit.id = 100;
    inject_flit.valid = true;
    inject_flit.src_ring = 0;
    inject_flit.src_node = 0;
    station.node_if[0].inject_q.push(inject_flit);

    // 3. Continuously block the output slot to trigger injection failures
    Flit blocker;
    blocker.id = 99;
    blocker.valid = true;
    blocker.dst_ring = 99;
    blocker.dst_node = 99; // Different destination so it just passes through

    bool swap_occurred = false;

    // Run enough cycles to trigger threshold (5) + 1 cycle for DRM action
    for (int cycle = 1; cycle <= 10; ++cycle) {
        // Block the slot every cycle
        ring.curr_cw_slots[0].occupied = true;
        ring.curr_cw_slots[0].flit = blocker;

        // Wait! In cycle 6, we want a flit that *wants* to eject to arrive
        // so that SWAP can actually happen. SWAP requires:
        // traversing flit wants to eject, eject queue full, inject queue ready.
        if (cycle >= 7) {
            Flit incoming_to_eject;
            incoming_to_eject.id = 200;
            incoming_to_eject.valid = true;
            incoming_to_eject.dst_ring = 0;
            incoming_to_eject.dst_node = 0; // Wants to eject here!
            ring.curr_cw_slots[0].flit = incoming_to_eject;
        }

        station.tick();

        ring.tock();
        station.tock();



        if (mock_sink.accepted_swaps > 0) {
            swap_occurred = true;
            // The injected flit should now be on the ring
            EXPECT_TRUE(ring.next_cw_slots[0].occupied);
            EXPECT_EQ(ring.next_cw_slots[0].flit.id, 100);

            // The incoming flit should have ejected (replacing the victim)
            EXPECT_EQ(station.node_if[0].eject_q.q.front().id, 200);
            break;
        }
    }

    EXPECT_TRUE(swap_occurred);
}

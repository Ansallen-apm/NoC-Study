#include <gtest/gtest.h>
#include "cross_station.hpp"
#include "ring.hpp"
#include <iostream>

// Test Phase 9/10: Functional Validation
class ValidationTest : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
};

TEST_F(ValidationTest, RoundRobinFairness) {
    Ring ring(0, 4, false);
    CrossStation station(0, &ring);

    // Fill both inject queues
    for (int i = 1; i <= 5; ++i) {
        Flit f1; f1.id = i; f1.valid = true;
        station.node_if[0].inject_q.push(f1);

        Flit f2; f2.id = i + 100; f2.valid = true;
        station.node_if[1].inject_q.push(f2);
    }

    int port0_injected = 0;
    int port1_injected = 0;

    for (int cycle = 0; cycle < 10; ++cycle) {
        station.tick();

        // Count who got injected
        if (ring.next_cw_slots[0].occupied) {
            if (ring.next_cw_slots[0].flit.id < 100) {
                port0_injected++;
            } else {
                port1_injected++;
            }
            // Clear slot for next injection
            ring.next_cw_slots[0].occupied = false;
        }

        station.tock();
    }

    // Total 10 injections. Should be exactly 5 from each.
    EXPECT_EQ(port0_injected, 5);
    EXPECT_EQ(port1_injected, 5);
}

TEST_F(ValidationTest, FlitConservation) {
    // Inject 100 flits into a single ring and let them circulate and eject.
    // Ensure that Flits Ejected + Flits in Queues + Flits on Ring = 100 at all times.
    Ring ring(0, 4, false);
    std::vector<std::unique_ptr<CrossStation>> stations;
    for (int i = 0; i < 4; ++i) {
        stations.push_back(std::make_unique<CrossStation>(i, &ring));
    }

    int total_injected = 100;
    for (int i = 1; i <= total_injected; ++i) {
        Flit f; f.id = i; f.valid = true; f.dst_node = i % 4;
        stations[0]->node_if[0].inject_q.q.push_back(f);
    }

    int total_ejected = 0;

    for (int cycle = 0; cycle < 200; ++cycle) {
        for (auto& st : stations) st->tick();
        ring.tick();

        for (auto& st : stations) st->tock();
        ring.tock();

        // Eject flits from all stations
        for (auto& st : stations) {
            for (int k = 0; k < 2; ++k) {
                while (!st->node_if[k].eject_q.q.empty()) {
                    st->node_if[k].eject_q.pop_oldest();
                    total_ejected++;
                }
            }
        }

        // Conservation check
        int flits_in_inject_q = 0;
        for (auto& st : stations) {
            flits_in_inject_q += st->node_if[0].inject_q.size();
            flits_in_inject_q += st->node_if[1].inject_q.size();
        }

        int flits_on_ring = 0;
        for (int i = 0; i < 4; ++i) {
            if (ring.curr_cw_slots[i].occupied) flits_on_ring++;
        }

        EXPECT_EQ(flits_in_inject_q + flits_on_ring + total_ejected, total_injected);
    }

    EXPECT_EQ(total_ejected, total_injected);
}

#include <gtest/gtest.h>
#include "simulator.hpp"
#include "cross_station.hpp"
#include <random>

TEST(ChaosStressTest, FlitConservationAndLiveness) {
    Simulator sim;
    ASSERT_TRUE(sim.init("../configs/ai_processor.yaml"));
    // build_from_config() is called by init()

    // Setup tiny buffers and deadlock threshold to provoke E-tag reservations
    for (auto* st : sim.stations) {
        if (!st) continue;
        st->node_if[0].eject_q.capacity = 1;
        st->node_if[1].eject_q.capacity = 1;
        st->node_if[0].eject_q.max_reservations = 1;
        st->node_if[1].eject_q.max_reservations = 1;
        st->node_if[0].inject_q.capacity = 2;
        st->node_if[1].inject_q.capacity = 2;
        st->set_deadlock_threshold(5);
    }

    std::mt19937 gen(1337);
    int total_injected = 0;
    int total_ejected = 0;

    for (int cycle = 0; cycle < 1000; ++cycle) {
        // 1. Inject uniformly randomly
        for (auto* st : sim.stations) {
            if (!st) continue;
            if (st->ring == nullptr) continue;
            if (gen() % 10 < 3) { // 30% injection rate per station per cycle
                for (int k = 0; k < 2; ++k) {
                    if (st->node_if[k].inject_q.can_push()) {
                        Flit f;
                        f.id = ++total_injected;
                        f.valid = true;
                        f.src_node = st->station_id;
                        f.src_ring = st->ring->ring_id;
                        // Random destination
                        f.dst_node = gen() % (st->ring->num_stations);
                        f.dst_ring = st->ring->ring_id;
                        st->node_if[k].inject_q.push(f);
                    }
                }
            }
        }

        // 2. Step the simulation
        sim.run(1);

        // 3. Eject with a probability to intentionally cause E-tag backpressure
        // We do NOT drain every cycle. We only drain 30% of the time, allowing queue to stay full
        for (auto* st : sim.stations) {
            if (!st) continue;
            if (gen() % 10 < 3) { // 30% chance to drain
                for (int k = 0; k < 2; ++k) {
                    while (!st->node_if[k].eject_q.q.empty()) {
                        st->node_if[k].eject_q.pop_oldest();
                        total_ejected++;
                    }
                }
            }
        }
    }

    // Drain completely at the end to check conservation
    for (int cycle = 0; cycle < 1000; ++cycle) {
        sim.run(1);
        for (auto* st : sim.stations) {
            if (!st) continue;
            for (int k = 0; k < 2; ++k) {
                while (!st->node_if[k].eject_q.q.empty()) {
                    st->node_if[k].eject_q.pop_oldest();
                    total_ejected++;
                }
            }
        }
    }

    int in_flight = 0;
    for (auto* r : sim.rings) {
        if (!r) continue;
        for (int i = 0; i < r->num_stations; ++i) {
            if (r->curr_cw_slots.size() > i && r->curr_cw_slots[i].occupied) in_flight++;
            if (r->bidirectional && r->curr_ccw_slots.size() > i && r->curr_ccw_slots[i].occupied) in_flight++;
        }
    }

    int in_queues = 0;
    for (auto* st : sim.stations) {
        if (!st) continue;
        in_queues += st->node_if[0].inject_q.size();
        in_queues += st->node_if[1].inject_q.size();
        in_queues += st->node_if[0].eject_q.size();
        in_queues += st->node_if[1].eject_q.size();
    }

    // We expect everything to be conserved
    EXPECT_EQ(total_ejected + in_flight + in_queues, total_injected);
    EXPECT_GT(total_ejected, 0); // Liveness: we did some work
}

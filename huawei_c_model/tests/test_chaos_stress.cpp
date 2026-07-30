#include <gtest/gtest.h>
#include "simulator.hpp"
#include "cross_station.hpp"
#include "stats.hpp"
#include <random>
#include <iostream>

TEST(ChaosStressTest, FlitConservationAndLiveness) {
    Simulator sim;
    ASSERT_TRUE(sim.init("../configs/server_cpu.yaml"));

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

    std::vector<std::pair<int, int>> all_nodes;
    for (auto* st : sim.stations) {
        if (st && st->ring) {
            all_nodes.push_back({st->ring->ring_id, st->station_id});
        }
    }

    for (int cycle = 0; cycle < 1000; ++cycle) {
        for (auto* st : sim.stations) {
            if (!st || st->ring == nullptr) continue;
            if (gen() % 10 < 3) {
                for (int k = 0; k < 2; ++k) {
                    if (st->node_if[k].inject_q.can_push()) {
                        Flit f;
                        f.id = ++total_injected;
                        f.valid = true;
                        f.src_node = st->station_id;
                        f.src_ring = st->ring->ring_id;

                        auto dest = all_nodes[gen() % all_nodes.size()];
                        f.dst_ring = dest.first;
                        f.dst_node = dest.second;

                        st->node_if[k].inject_q.push(f);
                    }
                }
            }
        }

        sim.run(1);

        for (auto* st : sim.stations) {
            if (!st) continue;
            if (gen() % 10 < 3) {
                for (int k = 0; k < 2; ++k) {
                    while (!st->node_if[k].eject_q.q.empty()) {
                        st->node_if[k].eject_q.pop_oldest();
                        total_ejected++;
                    }
                }
            }
        }
    }

    for (int cycle = 0; cycle < 20000; ++cycle) {
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

    int actual_in_flight = 0;
    for (auto* r : sim.rings) {
        if (!r) continue;
        for (int i = 0; i < r->num_stations; ++i) {
            if (r->curr_cw_slots.size() > i && r->curr_cw_slots[i].occupied) actual_in_flight++;
            if (r->bidirectional && r->curr_ccw_slots.size() > i && r->curr_ccw_slots[i].occupied) actual_in_flight++;
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

    int actual_in_bridges = 0;
    for (auto& component : sim.components) {
        auto b1 = dynamic_cast<RBRG_L1*>(component.get());
        if (b1) {
            actual_in_bridges += b1->ingress_queue.size() + b1->egress_queue.size();
            for (auto& reg : b1->pipeline_regs_curr) { if (reg.valid) actual_in_bridges++; }
        }
        auto b2 = dynamic_cast<RBRG_L2*>(component.get());
        if (b2) {
            actual_in_bridges += b2->local_rx_queue.size() + b2->remote_rx_queue.size() + b2->reserved_tx_buffer.size();
            for (auto& reg : b2->d2d_pipeline_curr) { if (reg.valid) actual_in_bridges++; }
        }
    }

    EXPECT_EQ(total_ejected + actual_in_flight + in_queues + actual_in_bridges, total_injected);
    EXPECT_GT(total_ejected, 0);

    EXPECT_GT(sim.stats.deflect_count, 0);
    EXPECT_GT(sim.stats.e_tag_create_count, 0);
    EXPECT_GT(sim.stats.i_tag_create_count, 0);
    EXPECT_GT(sim.stats.swap_count, 0);
}

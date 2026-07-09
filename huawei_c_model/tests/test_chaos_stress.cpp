#include <gtest/gtest.h>
#include "simulator.hpp"
#include <iostream>
#include <set>
#include <map>

// A custom uniform random generator for the chaos test
class ChaosGenerator : public TrafficGenerator {
public:
    ChaosGenerator(int s_ring, int s_station, CrossStation* station, std::shared_ptr<NodeDirectory> dir, int seed = 42)
        : TrafficGenerator(s_ring, s_station, station, dir, seed) {}

    void tick(double injection_rate) override {
        std::uniform_real_distribution<double> dist(0.0, 1.0);
        if (dist(rng) < injection_rate) {
            if (directory->all_nodes.empty()) return;

            // Pick any random destination globally
            std::uniform_int_distribution<int> node_dist(0, directory->all_nodes.size() - 1);
            auto target = directory->all_nodes[node_dist(rng)];

            for (int k = 0; k < 2; ++k) {
                if (attached_station->node_if[k].inject_q.can_push()) {
                    Flit f;
                    f.id = ++flit_id_counter; // Unique ID local to generator, we will offset it globally in test
                    f.valid = true;
                    f.src_ring = src_ring;
                    f.src_node = src_station;
                    f.dst_ring = target.ring_id;
                    f.dst_node = target.station_id;
                    f.dir = Direction::CW; // Or CCW, cross station handles shortest path if configured

                    attached_station->node_if[k].inject_q.push(f);
                    break;
                }
            }
        }
    }

    // Hack to adjust flit IDs so they are globally unique across all generators
    void set_id_offset(uint64_t offset) {
        flit_id_counter = offset;
    }
};


class ChaosSwapSink : public SwapSink {
public:
    std::vector<Flit> swallowed;
    bool can_accept_swap() const override { return true; }
    void accept_swap(const Flit& f) override { swallowed.push_back(f); }
};

class Phase28Test : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
};

TEST_F(Phase28Test, ChaosStressTest) {
    // 1. Build a 4x4 AI topology programmatically (without yaml to have full control of tiny buffers)
    Simulator sim;
    sim.node_dir = std::make_shared<NodeDirectory>();
    sim.global_router = std::make_shared<MultiRingRouter>();

    int num_v_rings = 4;
    int num_h_rings = 4;
    int stations_per_ring = 8;
    int deadlock_threshold = 10; // Very small to trigger DRM aggressively

    std::map<int, Ring*> v_ring_map;
    std::map<int, Ring*> h_ring_map;
    int next_ring_id = 0;

    auto build_rings = [&](int count, std::map<int, Ring*>& rmap) {
        for (int i = 0; i < count; ++i) {
            int r_id = next_ring_id++;
            auto r = std::make_unique<Ring>(r_id, stations_per_ring, true); // Bidirectional Full Rings
            rmap[i] = r.get();
            sim.rings.push_back(r.get());

            for (int s = 0; s < stations_per_ring; ++s) {
                auto st = std::make_unique<CrossStation>(s, r.get());
                st->set_deadlock_threshold(deadlock_threshold);

                // Extremely tiny buffers! Capacity = 1
                for (int k=0; k<2; ++k) {
                    st->node_if[k].inject_q.capacity = 1;
                    st->node_if[k].eject_q.capacity = 1;
                }

                sim.stations.push_back(st.get());
                sim.node_dir->add_node(r_id, s, "NODE");
                sim.add_component(std::move(st));
            }
            sim.add_component(std::move(r));
        }
    };

    build_rings(num_v_rings, v_ring_map);
    build_rings(num_h_rings, h_ring_map);

    // Build Intersections
    int h_spacing = stations_per_ring / num_v_rings;
    int v_spacing = stations_per_ring / num_h_rings;

    RBRGL1Config brg_cfg;
    brg_cfg.queue_depth = 1; // Tiny bridges!
    brg_cfg.latency_cycles = 2;

    for (int v = 0; v < num_v_rings; ++v) {
        for (int h = 0; h < num_h_rings; ++h) {
            int v_station = h * v_spacing;
            int h_station = v * h_spacing;

            auto bridge = std::make_unique<RBRG_L1>(
                v_ring_map[v]->ring_id, v_station,
                h_ring_map[h]->ring_id, h_station,
                brg_cfg, sim.global_router
            );
            bridge->set_local_ring(v_ring_map[v]);
            bridge->set_remote_ring(h_ring_map[h]);
            sim.add_component(std::move(bridge));
        }
    }

    std::vector<std::unique_ptr<ChaosSwapSink>> swap_sinks;
    for (auto* st : sim.stations) {
        auto sink = std::make_unique<ChaosSwapSink>();
        st->set_swap_sink(sink.get());
        swap_sinks.push_back(std::move(sink));
    }

    // Attach Chaos Generators
    uint64_t id_offset = 0;
    for (auto* st : sim.stations) {
        auto gen = std::make_unique<ChaosGenerator>(st->ring->ring_id, st->station_id, st, sim.node_dir, 42 + st->ring->ring_id + st->station_id);
        gen->set_id_offset(id_offset);
        sim.traffic_generators.push_back(std::move(gen));
        id_offset += 1000000;
    }


    std::set<uint64_t> injected_ids;
    std::set<uint64_t> accounted_ids;
    uint64_t total_injected = 0;
    uint64_t total_ejected = 0;
    uint64_t total_swaps = 0;

    int cycles = 50000;
    double injection_rate = 0.8;

    for (int i = 0; i < cycles; ++i) {
        for (size_t g = 0; g < sim.traffic_generators.size(); ++g) {
            auto* st = sim.stations[g];
            // To track accurately, just look at the flit IDs in the queue before and after.
            std::set<uint64_t> before_ids;
            for(const auto& f : st->node_if[0].inject_q.q) before_ids.insert(f.id);
            for(const auto& f : st->node_if[1].inject_q.q) before_ids.insert(f.id);

            sim.traffic_generators[g]->tick(injection_rate);

            std::set<uint64_t> after_ids;
            for(const auto& f : st->node_if[0].inject_q.q) after_ids.insert(f.id);
            for(const auto& f : st->node_if[1].inject_q.q) after_ids.insert(f.id);

            for(auto id : after_ids) {
                if(before_ids.find(id) == before_ids.end()) {
                    injected_ids.insert(id);
                    total_injected++;
                }
            }
        }

        for (auto& comp : sim.components) comp->tick();
        for (auto& comp : sim.components) comp->tock();

        for (auto* st : sim.stations) {
            for (int k = 0; k < 2; ++k) {
                while (!st->node_if[k].eject_q.q.empty()) {
                    Flit f = st->node_if[k].eject_q.pop_oldest();
                    accounted_ids.insert(f.id);
                    total_ejected++;
                }
            }
        }
    }

    for (auto& sink : swap_sinks) {
        total_swaps += sink->swallowed.size();
        for (auto& f : sink->swallowed) accounted_ids.insert(f.id);
    }

    uint64_t in_queues = 0;
    for (auto* st : sim.stations) {
        for(const auto& f : st->node_if[0].inject_q.q) { accounted_ids.insert(f.id); in_queues++; }
        for(const auto& f : st->node_if[1].inject_q.q) { accounted_ids.insert(f.id); in_queues++; }
        for(const auto& f : st->node_if[0].eject_q.q) { accounted_ids.insert(f.id); in_queues++; }
        for(const auto& f : st->node_if[1].eject_q.q) { accounted_ids.insert(f.id); in_queues++; }
    }

    uint64_t in_bridges = 0;
    for (auto& comp : sim.components) {
        if (auto* bridge = dynamic_cast<RBRG_L1*>(comp.get())) {
            for(const auto& f : bridge->ingress_queue) { accounted_ids.insert(f.id); in_bridges++; }
            for(const auto& f : bridge->egress_queue) { accounted_ids.insert(f.id); in_bridges++; }
            for (const auto& p : bridge->pipeline_regs_curr) {
                if (p.valid) { accounted_ids.insert(p.flit.id); in_bridges++; }
            }
        }
    }

    uint64_t on_rings = 0;
    for (auto* r : sim.rings) {
        for (int s = 0; s < r->num_stations; ++s) {
            if (r->curr_cw_slots[s].occupied) { accounted_ids.insert(r->curr_cw_slots[s].flit.id); on_rings++; }
            if (r->bidirectional && r->curr_ccw_slots[s].occupied) { accounted_ids.insert(r->curr_ccw_slots[s].flit.id); on_rings++; }
        }
    }

    std::cout << "Unique Injected: " << injected_ids.size() << " Computed: " << total_injected << std::endl;
    std::cout << "Unique Accounted: " << accounted_ids.size() << " Computed: " << (total_ejected + total_swaps + in_queues + in_bridges + on_rings) << std::endl;


    uint64_t accounted = total_ejected + total_swaps + in_queues + in_bridges + on_rings;

    EXPECT_EQ(accounted, total_injected) << "Flit Conservation Violated!";
    EXPECT_GT(total_swaps, 0) << "Expected SWAP to trigger under extreme chaos!";
}

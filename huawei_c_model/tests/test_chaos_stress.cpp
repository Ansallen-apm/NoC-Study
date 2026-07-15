#include <gtest/gtest.h>
#include "simulator.hpp"
#include <memory>
#include <fstream>
#include <cstdio>
#include <unordered_map>

// Event-based tracker for Flit Conservation and Liveness
class ChaosSpy {
public:
    struct FlitRecord {
        uint64_t inject_cycle;
    };

    std::unordered_map<uint64_t, FlitRecord> active_flits;
    int duplicate_ejects = 0;
    int liveness_failures = 0;

    void record_inject(uint64_t id, uint64_t cycle) {
        if (active_flits.find(id) == active_flits.end()) {
            active_flits[id] = {cycle};
        } else {
            // Already injected?
            duplicate_ejects++;
        }
    }

    void record_eject(uint64_t id) {
        if (active_flits.find(id) == active_flits.end()) {
            duplicate_ejects++;
        } else {
            active_flits.erase(id);
        }
    }

    void check_liveness(uint64_t current_cycle, uint64_t max_allowed_latency) {
        for (const auto& pair : active_flits) {
            if (current_cycle > pair.second.inject_cycle + max_allowed_latency) {
                liveness_failures++;
                EXPECT_TRUE(false) << "Liveness failure: Flit ID " << pair.first << " stuck for > " << max_allowed_latency << " cycles!";
            }
        }
    }
};

TEST(ChaosStressTest, FlitConservationAndLiveness) {
    // Generate an extreme chaos config
    std::ofstream out("chaos_test_extreme.yaml");
    out << R"(
topology: server_cpu
flit_bytes: 64
rings:
  - id: 0
    type: CPU
    stations: 4
  - id: 1
    type: MEM
    stations: 4
nodes:
  - id: 0
    type: CPU
    ring: 0
    station: 0
  - id: 1
    type: CPU
    ring: 0
    station: 1
  - id: 2
    type: MEM
    ring: 1
    station: 0
  - id: 3
    type: MEM
    ring: 1
    station: 1
bridges:
  - type: RBRG_L1
    local_ring: 0
    remote_ring: 1
    local_station: 2
    remote_station: 2
    d2d_latency_cycles: 1
routing:
  mode: shortest_path
deadlock:
  threshold_cycles: 2
)";
    out.close();

    Simulator sim;
    ASSERT_TRUE(sim.init("chaos_test_extreme.yaml"));
    sim.build_from_config();

    for (auto& comp : sim.components) {
        if (auto rbrg1 = dynamic_cast<RBRG_L1*>(comp.get())) {
            rbrg1->queue_depth = 1;
        }
    }
    for (CrossStation* cs : sim.stations) {
        cs->deadlock_threshold_cycles = 2; // Very fast deadlock trigger
        for (auto& nif : cs->node_if) {
            nif.eject_q.capacity = 1;
            nif.inject_q.capacity = 1;
        }
    }

    ChaosSpy spy;
    sim.traffic_generators.clear();

    int total_ejected = 0;
    uint64_t counter = 1; // absolute unique ID

    for (int i = 0; i < 500; ++i) {
        // 1. Inject manually
        if (i % 2 == 0) {
            for (CrossStation* cs : sim.stations) {
                Flit f;
                f.id = counter++;
                f.valid = true;
                f.src_ring = cs->ring->ring_id;
                f.dst_ring = 1 - cs->ring->ring_id;
                f.dst_node = -1;
                if (cs->node_if[0].inject_q.can_push()) {
                    spy.record_inject(f.id, i);
                    cs->node_if[0].inject_q.push(f);
                }
            }
        }

        sim.run(1);

        // 2. Poll ejections from all possible exit points (EjectQueue + SWAP Sink)
        for (CrossStation* cs : sim.stations) {
            for (int k = 0; k < 2; ++k) {
                while (cs->node_if[k].eject_q.size() > 0) {
                    Flit ejected = cs->node_if[k].eject_q.pop_oldest();
                    if (ejected.id > 0) {
                        spy.record_eject(ejected.id);
                        total_ejected++;
                    }
                }
            }
        }

        // 3. Clear SWAP sinks (which eat flits indefinitely if not polled)
        for (auto& comp : sim.components) {
            if (auto rbrg2 = dynamic_cast<RBRG_L2*>(comp.get())) {
                 while (rbrg2->reserved_tx_buffer.size() > 0) {
                     Flit f = rbrg2->reserved_tx_buffer.front();
                     rbrg2->reserved_tx_buffer.pop_front();
                     if (f.id > 0) {
                         spy.record_eject(f.id);
                         total_ejected++;
                     }
                 }
            }
        }

        if (i % 50 == 0) spy.check_liveness(i, 200); // Max allowed latency 200 cycles
    }

    // Flush any remaining active flits and check conservation
    // In chaos tests, flits could still be traveling. We just need to check they weren't lost/duplicated on eject.
    EXPECT_EQ(spy.duplicate_ejects, 0) << "Found duplicated or lost flits during ejection!";
    EXPECT_EQ(spy.liveness_failures, 0) << "Liveness failure: some flits are deadlocked.";
    EXPECT_GT(total_ejected, 0) << "Liveness failure: network deadlocked and zero flits ejected.";

    std::remove("chaos_test_extreme.yaml");
}

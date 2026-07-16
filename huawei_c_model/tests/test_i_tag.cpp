#include <gtest/gtest.h>
#include "simulator.hpp"
#include <fstream>
#include <memory>
#include <unordered_map>

class ITagSpy {
public:
    Simulator* sim;
    bool inject_success = false;
    uint64_t success_cycle = 0;

    ITagSpy(Simulator* s) : sim(s) {}

    void verify_cycle(uint64_t cycle) {
        // Track specifically if station 1 (id=1) has successfully injected flit ID 999.
        for (Ring* r : sim->rings) {
            for (const auto& slot : r->curr_cw_slots) {
                if (slot.occupied && slot.flit.id == 999) {
                    inject_success = true;
                    if (success_cycle == 0) success_cycle = cycle;
                }
            }
        }
    }
};

TEST(Phase3Test, ITagInjectionReservation_BlackBox) {
    // We create a tiny topology with just 4 stations on a single ring.
    std::ofstream out("itag_test.yaml");
    out << R"(
topology: server_cpu
flit_bytes: 64
rings:
  - id: 0
    type: full
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
    type: CPU
    ring: 0
    station: 2
  - id: 3
    type: CPU
    ring: 0
    station: 3
)";
    out.close();

    Simulator sim;
    ASSERT_TRUE(sim.init("itag_test.yaml"));
    sim.build_from_config();
    sim.traffic_generators.clear();

    ITagSpy spy(&sim);

    // Setup: Fill the ring with continuous traffic that bypasses station 1
    // to simulate high load and prevent station 1 from injecting naturally.
    // We will do this by injecting from station 0 continuously for 10 cycles first.

    for (int i = 0; i < 10; ++i) {
        for (CrossStation* cs : sim.stations) {
            if (cs->station_id == 0) {
                Flit f_block;
                f_block.id = 1000 + i;
                f_block.valid = true;
                f_block.src_node = 0;
                f_block.dst_node = 2; // Pass through station 1
                f_block.dir = Direction::CW;
                if (cs->node_if[0].inject_q.can_push()) {
                    cs->node_if[0].inject_q.push(f_block);
                }
            }
        }

        sim.run(1);

        // Remove flits at destination to free up eject Qs
        for (CrossStation* cs : sim.stations) {
            while (cs->node_if[0].eject_q.size() > 0) cs->node_if[0].eject_q.pop_oldest();
            while (cs->node_if[1].eject_q.size() > 0) cs->node_if[1].eject_q.pop_oldest();
        }
    }

    // Now attempt to inject flit 999 at station 1
    Flit f_target;
    f_target.id = 999;
    f_target.valid = true;
    f_target.src_node = 1;
    f_target.src_ring = 0;
    f_target.dst_node = 3;
    f_target.dst_ring = 0;
    f_target.dir = Direction::CW;

    for (CrossStation* cs : sim.stations) {
        if (cs->station_id == 1) {
            cs->node_if[0].inject_q.push(f_target);
        }
    }

    for (int i = 10; i < 60; ++i) {
        // Continuous blocking traffic from station 0 to station 2, going CW
        // This ensures the slot arriving at station 1 is always occupied.
        for (CrossStation* cs : sim.stations) {
            if (cs->station_id == 0) {
                Flit f_block;
                f_block.id = 1000 + i;
                f_block.valid = true;
                f_block.src_node = 0;
                f_block.dst_node = 2; // Pass through station 1
                f_block.dir = Direction::CW;
                if (cs->node_if[0].inject_q.can_push()) {
                    cs->node_if[0].inject_q.push(f_block);
                }
            }
        }

        sim.run(1);
        spy.verify_cycle(i);

        // Remove flits at destination to free up eject Qs
        for (CrossStation* cs : sim.stations) {
            while (cs->node_if[0].eject_q.size() > 0) cs->node_if[0].eject_q.pop_oldest();
            while (cs->node_if[1].eject_q.size() > 0) cs->node_if[1].eject_q.pop_oldest();
        }

        if (spy.inject_success) break;
    }

    // Thanks to I-tag mechanism, station 1 should be able to reserve a slot upstream
    // and successfully inject within a small bounded number of cycles (e.g., < 20).
    EXPECT_TRUE(spy.inject_success) << "I-tag failed: Flit starved and never injected under high load!";
    EXPECT_LT(spy.success_cycle, 10 + 30) << "I-tag failed: Took too long to resolve starvation.";

    std::remove("itag_test.yaml");
}

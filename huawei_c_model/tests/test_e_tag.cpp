#include <gtest/gtest.h>
#include "simulator.hpp"
#include <fstream>
#include <memory>
#include <iostream>

class ETagSpy {
public:
    Simulator* sim;
    bool eject_success = false;
    uint64_t success_cycle = 0;
    int target_deflect_count = 0;

    ETagSpy(Simulator* s) : sim(s) {}

    void verify_cycle(uint64_t cycle) {
        for (CrossStation* cs : sim->stations) {
            if (cs->station_id == 2) {
                for (const auto& f : cs->node_if[0].eject_q.q) {
                    if (f.id == 888) {
                        eject_success = true;
                        if (success_cycle == 0) success_cycle = cycle;
                        target_deflect_count = f.deflect_count;
                    }
                }
                for (const auto& f : cs->node_if[1].eject_q.q) {
                    if (f.id == 888) {
                        eject_success = true;
                        if (success_cycle == 0) success_cycle = cycle;
                        target_deflect_count = f.deflect_count;
                    }
                }
            }
        }
    }
};

TEST(Phase3Test, ETagEjectionDeflection_BlackBox) {
    std::ofstream out("etag_test.yaml");
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
    ASSERT_TRUE(sim.init("etag_test.yaml"));
    sim.build_from_config();
    sim.traffic_generators.clear();

    ETagSpy spy(&sim);

    // Setup: Restrict eject Q capacity at station 2 to exactly 1.
    for (CrossStation* cs : sim.stations) {
        if (cs->station_id == 2) {
            cs->node_if[0].eject_q.capacity = 1;
            cs->node_if[1].eject_q.capacity = 1;
        }
    }

    // Run 10 cycles to fill the queue
    for (int i = 0; i < 10; ++i) {
        // We inject from station 3 to station 2 going CCW.
        // It takes 1 cycle to reach station 2.
        for (CrossStation* cs : sim.stations) {
            if (cs->station_id == 3) {
                Flit f_block;
                f_block.id = 2000 + i;
                f_block.valid = true;
                f_block.src_node = 3;
                f_block.dst_node = 2;
                f_block.dir = Direction::CCW;
                if (cs->node_if[0].inject_q.can_push()) {
                    cs->node_if[0].inject_q.push(f_block);
                }
            }
        }
        sim.run(1);

        // Never pop from station 2 during setup, ensuring it stays full.
        for (CrossStation* cs : sim.stations) {
            if (cs->station_id != 2) {
                while (cs->node_if[0].eject_q.size() > 0) cs->node_if[0].eject_q.pop_oldest();
                while (cs->node_if[1].eject_q.size() > 0) cs->node_if[1].eject_q.pop_oldest();
            }
        }
    }

    // Now inject the target flit from station 0 to station 2.
    // It will arrive at station 2 in 2 cycles (CW).
    Flit f_target;
    f_target.id = 888;
    f_target.valid = true;
    f_target.src_node = 0;
    f_target.src_ring = 0;
    f_target.dst_node = 2;
    f_target.dst_ring = 0;
    f_target.dir = Direction::CW;

    for (CrossStation* cs : sim.stations) {
        if (cs->station_id == 0) cs->node_if[0].inject_q.push(f_target);
    }

    for (int i = 10; i < 50; ++i) {
        // Keep injecting blocking traffic from station 3 to keep queue full,
        for (CrossStation* cs : sim.stations) {
            if (cs->station_id == 3) {
                Flit f_block;
                f_block.id = 2000 + i;
                f_block.valid = true;
                f_block.src_node = 3;
                f_block.dst_node = 2;
                f_block.dir = Direction::CCW;
                if (cs->node_if[0].inject_q.can_push()) {
                    cs->node_if[0].inject_q.push(f_block);
                }
            }
        }

        sim.run(1);
        spy.verify_cycle(i);

        // Pop from station 2 only after we're sure flit 888 has been deflected.
        // It arrives at cycle 12. So we can start popping slowly around cycle 14.
        for (CrossStation* cs : sim.stations) {
            if (cs->station_id == 2 && i >= 14 && i % 4 == 0) {
                // Only pop if the queue is actually full, and don't pop the E-tag reserved spot
                // Wait, if we pop, it frees up space. The blocking traffic is CCW.
                // The target traffic is CW.
                // If E-tag works, it reserves a spot for CW.
                if (cs->node_if[0].eject_q.size() > 0) cs->node_if[0].eject_q.pop_oldest();
                if (cs->node_if[1].eject_q.size() > 0) cs->node_if[1].eject_q.pop_oldest();
            } else if (cs->station_id != 2) {
                while (cs->node_if[0].eject_q.size() > 0) cs->node_if[0].eject_q.pop_oldest();
                while (cs->node_if[1].eject_q.size() > 0) cs->node_if[1].eject_q.pop_oldest();
            }
        }

        if (spy.eject_success) break;
    }

    EXPECT_TRUE(spy.eject_success) << "E-tag failed: Flit livelocked and never ejected!";
    EXPECT_LT(spy.success_cycle, 40) << "E-tag failed: Took too long to resolve livelock.";
    EXPECT_GT(spy.target_deflect_count, 0) << "E-tag test invalid: Flit was never deflected!";
    EXPECT_LE(spy.target_deflect_count, 2) << "E-tag test invalid: Flit was deflected too many times (E-tag not working effectively)!";

    std::remove("etag_test.yaml");
}

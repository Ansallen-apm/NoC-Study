#include <gtest/gtest.h>
#include "simulator.hpp"
#include <fstream>
#include <memory>

class ETagSpy {
public:
    Simulator* sim;
    bool eject_success = false;
    uint64_t success_cycle = 0;

    ETagSpy(Simulator* s) : sim(s) {}

    void verify_cycle(uint64_t cycle) {
        for (CrossStation* cs : sim->stations) {
            if (cs->station_id == 2) {
                // Check if flit 888 reached station 2 eject queue
                for (const auto& f : cs->node_if[0].eject_q.q) {
                    if (f.id == 888) {
                        eject_success = true;
                        if (success_cycle == 0) success_cycle = cycle;
                    }
                }
                for (const auto& f : cs->node_if[1].eject_q.q) {
                    if (f.id == 888) {
                        eject_success = true;
                        if (success_cycle == 0) success_cycle = cycle;
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
    // We will fill it constantly with traffic from station 1 so that our target flit from station 0
    // always gets deflected.
    for (CrossStation* cs : sim.stations) {
        if (cs->station_id == 2) {
            cs->node_if[0].eject_q.capacity = 1;
            cs->node_if[1].eject_q.capacity = 1;
        }
    }

    // Target flit from station 0 to station 2
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

    for (int i = 0; i < 50; ++i) {
        // Continuous blocking traffic from station 1 to station 2, going CW
        // This hits station 2 just before station 0's flit arrives or simultaneously
        for (CrossStation* cs : sim.stations) {
            if (cs->station_id == 1) {
                Flit f_block;
                f_block.id = 2000 + i;
                f_block.valid = true;
                f_block.src_node = 1;
                f_block.dst_node = 2;
                f_block.dir = Direction::CW;
                if (cs->node_if[0].inject_q.can_push()) {
                    cs->node_if[0].inject_q.push(f_block);
                }
            }
        }

        sim.run(1);
        spy.verify_cycle(i);

        // At station 2, we pop 1 item to simulate slow consumption, but since it has capacity 1
        // and we inject 1 every cycle from station 1, it might stay full for the deflected flit
        for (CrossStation* cs : sim.stations) {
            if (cs->station_id == 2 && i % 4 == 0) { // pop slowly, E-tag will guarantee it catches it
                if (cs->node_if[0].eject_q.size() > 0) cs->node_if[0].eject_q.pop_oldest();
                if (cs->node_if[1].eject_q.size() > 0) cs->node_if[1].eject_q.pop_oldest();
            } else if (cs->station_id != 2) {
                while (cs->node_if[0].eject_q.size() > 0) cs->node_if[0].eject_q.pop_oldest();
                while (cs->node_if[1].eject_q.size() > 0) cs->node_if[1].eject_q.pop_oldest();
            }
        }

        if (spy.eject_success) break;
    }

    // Thanks to E-tag mechanism, the deflected flit 888 should have reserved a slot
    // and successfully ejected on its next round trip (e.g. < 20 cycles).
    EXPECT_TRUE(spy.eject_success) << "E-tag failed: Flit livelocked and never ejected!";
    EXPECT_LT(spy.success_cycle, 30) << "E-tag failed: Took too long to resolve livelock.";

    std::remove("etag_test.yaml");
}

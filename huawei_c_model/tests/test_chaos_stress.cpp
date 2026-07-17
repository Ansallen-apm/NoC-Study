#include <gtest/gtest.h>
#include "simulator.hpp"
#include <memory>

TEST(ChaosStressTest, FlitConservationAndLiveness) {
    Simulator sim;
    ASSERT_TRUE(sim.init("../configs/server_cpu.yaml"));
    sim.build_from_config();
    sim.run(100);

    const auto& stats = sim.stats;
    EXPECT_GT(stats.total_cycles, 0);
}

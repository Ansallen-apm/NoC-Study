#include <gtest/gtest.h>
#include "simulator.hpp"

class DummyComponent : public Component {
public:
    int tick_count = 0;
    int tock_count = 0;

    void tick() override { tick_count++; }
    void tock() override { tock_count++; }
};

TEST(SimulatorTest, BasicCycleLoop) {
    Simulator sim;
    ASSERT_TRUE(sim.init("../configs/server_cpu.yaml"));

    auto comp = std::make_unique<DummyComponent>();
    DummyComponent* ptr = comp.get();
    sim.add_component(std::move(comp));

    sim.run(10);

    EXPECT_EQ(sim.stats.total_cycles, 10);
    EXPECT_EQ(ptr->tick_count, 10);
    EXPECT_EQ(ptr->tock_count, 10);
}

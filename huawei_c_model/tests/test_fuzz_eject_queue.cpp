#include <gtest/gtest.h>
#include "node_interface.hpp"
#include <random>

TEST(EjectQueue, FuzzCapacityInvariant) {
    EjectQueue eq;
    eq.capacity = 1;
    eq.max_reservations = 1;

    std::mt19937 rng(42); // Fixed seed for reproducibility
    std::uniform_int_distribution<int> op_dist(0, 2); // 0: push, 1: pop, 2: reserve

    uint64_t next_flit_id = 1;

    for (int i = 0; i < 10000; ++i) {
        int op = op_dist(rng);

        if (op == 0) {
            // Try to push
            Flit f;
            // Let's sometimes try to push a reserved flit, sometimes a random new one
            if (!eq.reserved_flit_ids.empty() && rng() % 2 == 0) {
                f.id = *eq.reserved_flit_ids.begin();
            } else {
                f.id = next_flit_id++;
            }
            eq.push(f);
        } else if (op == 1) {
            // Try to pop
            eq.pop_oldest();
        } else if (op == 2) {
            // Try to reserve
            eq.reserve(next_flit_id++);
        }

        // The critical invariant: physical size MUST NEVER exceed capacity
        EXPECT_LE(eq.size(), eq.capacity) << "Capacity invariant violated at iteration " << i;
    }
}

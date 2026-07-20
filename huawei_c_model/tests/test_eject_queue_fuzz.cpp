#include <gtest/gtest.h>
#include "node_interface.hpp"
#include <random>

TEST(EjectQueueFuzzTest, FuzzCapacityInvariant) {
    EjectQueue eq;
    eq.capacity = 1;
    eq.max_reservations = 1;

    std::mt19937 gen(42);
    std::uniform_int_distribution<> action_dist(0, 2);

    uint64_t next_flit_id = 1;
    uint64_t reserved_id = 0;

    for (int i = 0; i < 100000; ++i) {
        int action = action_dist(gen);

        if (action == 0) {
            // Try to reserve
            if (eq.can_reserve()) {
                reserved_id = next_flit_id++;
                eq.reserve(reserved_id);
            }
        } else if (action == 1) {
            // Try to push
            Flit f;
            // 50% chance to push the reserved flit if we have one
            if (reserved_id != 0 && (gen() % 2 == 0)) {
                f.id = reserved_id;
                reserved_id = 0; // We consume it on our end
            } else {
                f.id = next_flit_id++;
            }
            eq.push(f);
        } else {
            // Try to pop
            if (eq.size() > 0) {
                eq.pop_oldest();
            }
        }

        // The critical invariant!
        EXPECT_LE(eq.size(), eq.capacity);
    }
}

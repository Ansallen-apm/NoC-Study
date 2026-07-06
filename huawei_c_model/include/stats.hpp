#ifndef STATS_HPP
#define STATS_HPP

#include <cstdint>

class StatCollector {
public:
    StatCollector() = default;
    void tick();
    void tock();

    // Add simple metrics for skeleton
    uint64_t total_cycles = 0;
};

#endif // STATS_HPP

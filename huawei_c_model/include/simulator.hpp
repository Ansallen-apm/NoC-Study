#ifndef SIMULATOR_HPP
#define SIMULATOR_HPP

#include "config.hpp"
#include "stats.hpp"
#include "trace.hpp"
#include "component.hpp"
#include <vector>
#include <memory>

class Simulator {
public:
    Config config;
    StatCollector stats;
    TraceDumper trace;

    std::vector<std::unique_ptr<Component>> components;

    bool init(const std::string& config_path);
    void run(uint64_t cycles);

    void add_component(std::unique_ptr<Component> comp);
};

#endif // SIMULATOR_HPP

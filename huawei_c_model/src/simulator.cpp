#include "simulator.hpp"
#include <iostream>

bool Simulator::init(const std::string& config_path) {
    if (!config.parse(config_path)) {
        std::cerr << "Failed to parse config: " << config_path << "\n";
        return false;
    }
    return true;
}

void Simulator::run(uint64_t cycles) {
    for (uint64_t i = 0; i < cycles; ++i) {
        // Phase 1: Tick (compute next state)
        for (auto& comp : components) {
            comp->tick();
        }
        stats.tick();
        trace.tick();

        // Phase 2: Tock (commit state)
        for (auto& comp : components) {
            comp->tock();
        }
        stats.tock();
        trace.tock();
    }
}

void Simulator::add_component(std::unique_ptr<Component> comp) {
    components.push_back(std::move(comp));
}

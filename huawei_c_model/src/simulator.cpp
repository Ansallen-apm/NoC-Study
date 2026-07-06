#include "simulator.hpp"
#include <iostream>

#include "ring.hpp"
#include "cross_station.hpp"

bool Simulator::init(const std::string& config_path) {
    if (!config.parse(config_path)) {
        std::cerr << "Failed to parse config: " << config_path << "\n";
        return false;
    }

    init_topology();

    return true;
}

void Simulator::instantiate_server_cpu() {
    for (const auto& rc : config.rings) {
        bool bidir = (rc.type == "full");
        auto r = std::make_unique<Ring>(rc.id, rc.stations, bidir);
        rings.push_back(r.get());

        for (int i = 0; i < rc.stations; ++i) {
            auto s = std::make_unique<CrossStation>(i, r.get());
            stations.push_back(s.get());
            add_component(std::move(s));
        }
        add_component(std::move(r));
    }
}

void Simulator::instantiate_ai_processor() {
    // Basic AI processor instantiation structure
    int ring_id = 0;

    if (config.vertical_rings.has_value()) {
        auto& vr = config.vertical_rings.value();
        bool bidir = (vr.type == "full");
        for (int i = 0; i < vr.count; ++i) {
            auto r = std::make_unique<Ring>(ring_id++, vr.stations_per_ring, bidir);
            rings.push_back(r.get());
            for (int s_idx = 0; s_idx < vr.stations_per_ring; ++s_idx) {
                auto s = std::make_unique<CrossStation>(s_idx, r.get());
                stations.push_back(s.get());
                add_component(std::move(s));
            }
            add_component(std::move(r));
        }
    }

    if (config.horizontal_rings.has_value()) {
        auto& hr = config.horizontal_rings.value();
        bool bidir = (hr.type == "full");
        for (int i = 0; i < hr.count; ++i) {
            auto r = std::make_unique<Ring>(ring_id++, hr.stations_per_ring, bidir);
            rings.push_back(r.get());
            for (int s_idx = 0; s_idx < hr.stations_per_ring; ++s_idx) {
                auto s = std::make_unique<CrossStation>(s_idx, r.get());
                stations.push_back(s.get());
                add_component(std::move(s));
            }
            add_component(std::move(r));
        }
    }
}

void Simulator::init_topology() {
    if (config.topology == "server_cpu") {
        instantiate_server_cpu();
    } else if (config.topology == "ai_processor") {
        instantiate_ai_processor();
    } else if (config.topology == "test_single_ring") {
        // Special simple config for Phase 1 tests
        auto r = std::make_unique<Ring>(0, 4, false); // 4 stations, CW only
        rings.push_back(r.get());
        for (int i = 0; i < 4; ++i) {
            auto s = std::make_unique<CrossStation>(i, r.get());
            stations.push_back(s.get());
            add_component(std::move(s));
        }
        add_component(std::move(r));
    } else if (config.topology == "test_full_ring") {
        // Special simple config for Phase 2 tests
        auto r = std::make_unique<Ring>(0, 8, true); // 8 stations, full ring
        rings.push_back(r.get());
        for (int i = 0; i < 8; ++i) {
            auto s = std::make_unique<CrossStation>(i, r.get());
            stations.push_back(s.get());
            add_component(std::move(s));
        }
        add_component(std::move(r));
    }
}

void Simulator::run(uint64_t cycles) {
    for (uint64_t i = 0; i < cycles; ++i) {
        // 1. tick() evaluates next state without committing (reads current state)
        for (auto& comp : components) {
            comp->tick();
        }

        stats.tick();
        trace.tick();

        // 2. tock() commits the state for all components (writes next state to current)
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

#include "simulator.hpp"
#include <iostream>

#include "ring.hpp"
#include "cross_station.hpp"

void Simulator::build_from_config() {
    node_dir = std::make_shared<NodeDirectory>();
    global_router = std::make_shared<MultiRingRouter>();

    int deadlock_threshold = config.deadlock ? config.deadlock->threshold_cycles : 64;

    if (config.topology == "server_cpu") {
        std::map<int, Ring*> ring_map;

        for (const auto& rcfg : config.rings) {
            bool is_bidir = (rcfg.type == "full");
            auto r = std::make_unique<Ring>(rcfg.id, rcfg.stations, is_bidir);
            ring_map[rcfg.id] = r.get();
            rings.push_back(r.get());

            for (int s = 0; s < rcfg.stations; ++s) {
                auto st = std::make_unique<CrossStation>(s, r.get());
                st->set_deadlock_threshold(deadlock_threshold);
                stations.push_back(st.get());
                add_component(std::move(st));
            }
            add_component(std::move(r));
        }

        for (const auto& ncfg : config.nodes) {
            node_dir->add_node(ncfg.ring, ncfg.station, ncfg.type);
        }

        for (const auto& bcfg : config.bridges) {
            if (bcfg.type == "RBRG_L2") {
                auto bridge = std::make_unique<RBRG_L2>(
                    bcfg.local_ring, bcfg.local_station,
                    bcfg.remote_ring, bcfg.remote_station,
                    bcfg, 4, 16, global_router
                );
                bridge->set_local_ring(ring_map[bcfg.local_ring]);
                bridge->set_remote_ring(ring_map[bcfg.remote_ring]);

                for (auto* st : stations) {
                    if (st->station_id == bcfg.local_station && st->ring->ring_id == bcfg.local_ring) {
                        st->set_swap_sink(bridge.get());
                        break;
                    }
                }
                add_component(std::move(bridge));
            }
        }
    } else if (config.topology == "ai_processor") {
        std::map<int, Ring*> v_ring_map;
        std::map<int, Ring*> h_ring_map;
        int next_ring_id = 0;

        auto build_multi_ring = [&](const MultiRingConfig& mrc, std::map<int, Ring*>& rmap, bool is_vertical, const std::vector<NodeConfig>& node_cfgs) {
            bool is_bidir = (mrc.type == "full");
            for (int i = 0; i < mrc.count; ++i) {
                int r_id = next_ring_id++;
                auto r = std::make_unique<Ring>(r_id, mrc.stations_per_ring, is_bidir);
                rmap[i] = r.get();
                rings.push_back(r.get());

                for (int s = 0; s < mrc.stations_per_ring; ++s) {
                    auto st = std::make_unique<CrossStation>(s, r.get());
                    st->set_deadlock_threshold(deadlock_threshold);
                    stations.push_back(st.get());
                    add_component(std::move(st));
                }

                int current_station = 0;
                for (const auto& nc : node_cfgs) {
                    for (int c = 0; c < nc.count_per_ring; ++c) {
                        node_dir->add_node(r_id, current_station, nc.type);
                        current_station += 2;
                    }
                }

                add_component(std::move(r));
            }
        };

        if (config.vertical_rings) build_multi_ring(*config.vertical_rings, v_ring_map, true, config.vertical_nodes);
        if (config.horizontal_rings) build_multi_ring(*config.horizontal_rings, h_ring_map, false, config.horizontal_nodes);

        if (config.rbrg_l1 && config.rbrg_l1->at_each_intersection) {
            int h_spacing = config.horizontal_rings->stations_per_ring / config.vertical_rings->count;
            int v_spacing = config.vertical_rings->stations_per_ring / config.horizontal_rings->count;

            for (int v = 0; v < config.vertical_rings->count; ++v) {
                for (int h = 0; h < config.horizontal_rings->count; ++h) {
                    int v_station = h * v_spacing;
                    int h_station = v * h_spacing;

                    auto bridge = std::make_unique<RBRG_L1>(
                        v_ring_map[v]->ring_id, v_station,
                        h_ring_map[h]->ring_id, h_station,
                        *config.rbrg_l1, global_router
                    );
                    bridge->set_local_ring(v_ring_map[v]);
                    bridge->set_remote_ring(h_ring_map[h]);
                    add_component(std::move(bridge));
                }
            }
        }
    }
}


bool Simulator::init(const std::string& config_path) {
    if (!config.parse(config_path)) {
        std::cerr << "Failed to parse config: " << config_path << "\n";
        return false;
    }

    build_from_config();

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

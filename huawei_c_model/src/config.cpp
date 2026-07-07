#include "config.hpp"
#include <yaml-cpp/yaml.h>
#include <iostream>

bool Config::parse(const std::string& filepath) {
    try {
        YAML::Node config = YAML::LoadFile(filepath);

        if (config["topology"]) {
            topology = config["topology"].as<std::string>();
        }
        if (config["flit_bytes"]) {
            flit_bytes = config["flit_bytes"].as<int>();
        }

        // Parse Server-CPU specifics
        if (config["rings"]) {
            for (const auto& r : config["rings"]) {
                RingConfig rc;
                if (r["id"]) rc.id = r["id"].as<int>();
                if (r["die"]) rc.die = r["die"].as<std::string>();
                if (r["type"]) rc.type = r["type"].as<std::string>();
                if (r["stations"]) rc.stations = r["stations"].as<int>();
                rings.push_back(rc);
            }
        }

        if (config["nodes"] && config["nodes"].IsSequence()) {
            for (const auto& n : config["nodes"]) {
                NodeConfig nc;
                nc.count_per_ring = 0; // default
                if (n["id"]) nc.id = n["id"].as<int>();
                if (n["type"]) nc.type = n["type"].as<std::string>();
                if (n["ring"]) nc.ring = n["ring"].as<int>();
                if (n["station"]) nc.station = n["station"].as<int>();
                nodes.push_back(nc);
            }
        }

        if (config["bridges"]) {
            for (const auto& b : config["bridges"]) {
                BridgeConfig bc;
                if (b["type"]) bc.type = b["type"].as<std::string>();
                if (b["local_ring"]) bc.local_ring = b["local_ring"].as<int>();
                if (b["remote_ring"]) bc.remote_ring = b["remote_ring"].as<int>();
                if (b["local_station"]) bc.local_station = b["local_station"].as<int>();
                if (b["remote_station"]) bc.remote_station = b["remote_station"].as<int>();
                if (b["d2d_latency_cycles"]) bc.d2d_latency_cycles = b["d2d_latency_cycles"].as<int>();
                bridges.push_back(bc);
            }
        }

        // Parse AI-Processor specifics
        if (config["vertical_rings"]) {
            MultiRingConfig mrc;
            if (config["vertical_rings"]["count"]) mrc.count = config["vertical_rings"]["count"].as<int>();
            if (config["vertical_rings"]["type"]) mrc.type = config["vertical_rings"]["type"].as<std::string>();
            if (config["vertical_rings"]["stations_per_ring"]) mrc.stations_per_ring = config["vertical_rings"]["stations_per_ring"].as<int>();
            vertical_rings = mrc;
        }

        if (config["horizontal_rings"]) {
            MultiRingConfig mrc;
            if (config["horizontal_rings"]["count"]) mrc.count = config["horizontal_rings"]["count"].as<int>();
            if (config["horizontal_rings"]["type"]) mrc.type = config["horizontal_rings"]["type"].as<std::string>();
            if (config["horizontal_rings"]["stations_per_ring"]) mrc.stations_per_ring = config["horizontal_rings"]["stations_per_ring"].as<int>();
            horizontal_rings = mrc;
        }

        if (config["rbrg_l1"]) {
            RBRGL1Config r1c;
            if (config["rbrg_l1"]["at_each_intersection"]) r1c.at_each_intersection = config["rbrg_l1"]["at_each_intersection"].as<bool>();
            if (config["rbrg_l1"]["queue_depth"]) r1c.queue_depth = config["rbrg_l1"]["queue_depth"].as<int>();
            if (config["rbrg_l1"]["latency_cycles"]) r1c.latency_cycles = config["rbrg_l1"]["latency_cycles"].as<int>();
            rbrg_l1 = r1c;
        } else {
            // Provide default if not in config but requested by architecture
            rbrg_l1 = RBRGL1Config();
        }

        if (config["nodes"] && config["nodes"].IsMap()) {
            if (config["nodes"]["vertical"]) {
                 for (const auto& n : config["nodes"]["vertical"]) {
                     NodeConfig nc;
                     if (n["type"]) nc.type = n["type"].as<std::string>();
                     if (n["count_per_ring"]) nc.count_per_ring = n["count_per_ring"].as<int>();
                     vertical_nodes.push_back(nc);
                 }
            }
            if (config["nodes"]["horizontal"]) {
                 for (const auto& n : config["nodes"]["horizontal"]) {
                     NodeConfig nc;
                     if (n["type"]) nc.type = n["type"].as<std::string>();
                     if (n["count_per_ring"]) nc.count_per_ring = n["count_per_ring"].as<int>();
                     horizontal_nodes.push_back(nc);
                 }
            }
        }

        if (config["routing"]) {
            RoutingConfig rc;
            if (config["routing"]["mode"]) rc.mode = config["routing"]["mode"].as<std::string>();
            routing = rc;
        }

        if (config["deadlock"]) {
            DeadlockConfig dc;
            if (config["deadlock"]["threshold_cycles"]) dc.threshold_cycles = config["deadlock"]["threshold_cycles"].as<int>();
            deadlock = dc;
        } else {
            deadlock = DeadlockConfig(); // Defaults
        }

        return true;
    } catch (const YAML::Exception& e) {
        std::cerr << "YAML parsing error: " << e.what() << "\n";
        return false;
    }
}

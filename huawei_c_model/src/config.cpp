#include "config.hpp"
#include <yaml-cpp/yaml.h>
#include <iostream>
#include <stdexcept>

bool Config::parse(const std::string& filepath) {
    try {
        YAML::Node config = YAML::LoadFile(filepath);

        if (config["topology"]) {
            topology = config["topology"].as<std::string>();
        } else {
            throw std::runtime_error("Config missing required 'topology' field");
        }
        if (config["flit_bytes"]) {
            flit_bytes = config["flit_bytes"].as<int>();
        }

        // Parse Server-CPU specifics
        if (config["rings"]) {
            for (const auto& r : config["rings"]) {
                RingConfig rc;
                if (!r["id"]) throw std::runtime_error("Ring config missing 'id'");
                rc.id = r["id"].as<int>();
                if (!r["type"]) throw std::runtime_error("Ring config missing 'type'");
                rc.type = r["type"].as<std::string>();
                if (!r["stations"]) throw std::runtime_error("Ring config missing 'stations'");
                rc.stations = r["stations"].as<int>();
                if (rc.stations <= 0) throw std::runtime_error("Ring 'stations' must be > 0");
                if (r["die"]) rc.die = r["die"].as<std::string>();
                else rc.die = "cpu";
                rings.push_back(rc);
            }
        }

        if (config["nodes"] && config["nodes"].IsSequence()) {
            for (const auto& n : config["nodes"]) {
                NodeConfig nc;
                nc.count_per_ring = 0; // default
                if (!n["id"] || !n["type"] || !n["ring"] || !n["station"]) {
                    throw std::runtime_error("Node config missing id, type, ring or station");
                }
                nc.id = n["id"].as<int>();
                nc.type = n["type"].as<std::string>();
                nc.ring = n["ring"].as<int>();
                nc.station = n["station"].as<int>();
                nodes.push_back(nc);
            }
        }

        if (config["bridges"]) {
            for (const auto& b : config["bridges"]) {
                BridgeConfig bc;
                if (!b["type"] || !b["local_ring"] || !b["remote_ring"] || !b["local_station"] || !b["remote_station"]) {
                    throw std::runtime_error("Bridge config missing required fields");
                }
                bc.type = b["type"].as<std::string>();
                bc.local_ring = b["local_ring"].as<int>();
                bc.remote_ring = b["remote_ring"].as<int>();
                bc.local_station = b["local_station"].as<int>();
                bc.remote_station = b["remote_station"].as<int>();
                if (b["d2d_latency_cycles"]) bc.d2d_latency_cycles = b["d2d_latency_cycles"].as<int>();
                else bc.d2d_latency_cycles = 1;
                bridges.push_back(bc);
            }
        }

        // Parse AI-Processor specifics
        if (config["vertical_rings"]) {
            MultiRingConfig mrc;
            if (!config["vertical_rings"]["count"] || !config["vertical_rings"]["type"] || !config["vertical_rings"]["stations_per_ring"]) {
                 throw std::runtime_error("vertical_rings missing required fields");
            }
            mrc.count = config["vertical_rings"]["count"].as<int>();
            mrc.type = config["vertical_rings"]["type"].as<std::string>();
            mrc.stations_per_ring = config["vertical_rings"]["stations_per_ring"].as<int>();
            if (mrc.stations_per_ring <= 0 || mrc.count <= 0) throw std::runtime_error("vertical_rings count/stations must be > 0");
            vertical_rings = mrc;
        }

        if (config["horizontal_rings"]) {
            MultiRingConfig mrc;
            if (!config["horizontal_rings"]["count"] || !config["horizontal_rings"]["type"] || !config["horizontal_rings"]["stations_per_ring"]) {
                 throw std::runtime_error("horizontal_rings missing required fields");
            }
            mrc.count = config["horizontal_rings"]["count"].as<int>();
            mrc.type = config["horizontal_rings"]["type"].as<std::string>();
            mrc.stations_per_ring = config["horizontal_rings"]["stations_per_ring"].as<int>();
            if (mrc.stations_per_ring <= 0 || mrc.count <= 0) throw std::runtime_error("horizontal_rings count/stations must be > 0");
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
                     if (!n["type"] || !n["count_per_ring"]) {
                         throw std::runtime_error("Node config missing type or count_per_ring in vertical nodes");
                     }
                     NodeConfig nc;
                     nc.type = n["type"].as<std::string>();
                     nc.count_per_ring = n["count_per_ring"].as<int>();
                     vertical_nodes.push_back(nc);
                 }
            }
            if (config["nodes"]["horizontal"]) {
                 for (const auto& n : config["nodes"]["horizontal"]) {
                     if (!n["type"] || !n["count_per_ring"]) {
                         throw std::runtime_error("Node config missing type or count_per_ring in horizontal nodes");
                     }
                     NodeConfig nc;
                     nc.type = n["type"].as<std::string>();
                     nc.count_per_ring = n["count_per_ring"].as<int>();
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
    } catch (const std::runtime_error& e) {
        std::cerr << "Config validation error: " << e.what() << "\n";
        return false;
    }
}

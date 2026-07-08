#include "simulator.hpp"
#include <iostream>
#include <fstream>

void run_server_experiment(const std::string& config_file) {
    std::cout << "Running Server-CPU Experiment..." << std::endl;

    std::ofstream out_file("../../reports/huawei_c_model/server_latency.csv");
    out_file << "injection_rate,average_latency,received_flits,avg_utilization\n";

    std::vector<double> rates = {0.05, 0.1, 0.15, 0.2, 0.25, 0.3};
    for (double rate : rates) {
        Simulator sim;
        if (!sim.init(config_file)) return;

        for (auto* st : sim.stations) {
            auto nodes = sim.node_dir->all_nodes;
            for (const auto& n : nodes) {
                if (n.ring_id == st->ring->ring_id && n.station_id == st->station_id && n.type == "CPU_CLUSTER") {
                    std::vector<std::string> targets = {"DDRC"};
                    auto gen = std::make_unique<HotspotGenerator>(n.ring_id, n.station_id, st, sim.node_dir, targets);
                    sim.traffic_generators.push_back(std::move(gen));
                }
            }
        }

        int warm_up = 1000;
        int sim_cycles = 5000;
        uint64_t total_latency = 0;
        uint64_t total_received = 0;

        for (int i = 0; i < warm_up + sim_cycles; ++i) {
            for (auto& gen : sim.traffic_generators) gen->tick(rate);
            for (auto& comp : sim.components) comp->tick();
            for (auto& comp : sim.components) comp->tock();

            for (auto* st : sim.stations) {
                auto nodes = sim.node_dir->all_nodes;
                for (const auto& n : nodes) {
                    if (n.ring_id == st->ring->ring_id && n.station_id == st->station_id && n.type == "DDRC") {
                        for (int k = 0; k < 2; ++k) {
                            while (!st->node_if[k].eject_q.q.empty()) {
                                Flit f = st->node_if[k].eject_q.pop_oldest();
                                if (i >= warm_up) {
                                    total_latency += f.eject_cycle;
                                    total_received++;
                                }
                            }
                        }
                    }
                }
            }
        }

        uint64_t total_active = 0;
        uint64_t total_slots = 0;
        for (auto* r : sim.rings) {
            for (int s = 0; s < r->num_stations; ++s) {
                total_active += r->active_cycles_cw[s];
                total_slots += (warm_up + sim_cycles);
                if (r->bidirectional) {
                    total_active += r->active_cycles_ccw[s];
                    total_slots += (warm_up + sim_cycles);
                }
            }
        }
        double avg_util = total_slots > 0 ? (double)total_active / total_slots : 0;
        double avg_lat = total_received > 0 ? (double)total_latency / total_received : 0;
        std::cout << "Rate: " << rate << " | Avg Latency: " << avg_lat << " | Util: " << avg_util << std::endl;
        out_file << rate << "," << avg_lat << "," << total_received << "," << avg_util << "\n";
    }
    out_file.close();
}

void run_ai_experiment(const std::string& config_file) {
    std::cout << "Running AI-Processor Experiment..." << std::endl;

    std::ofstream out_file("../../reports/huawei_c_model/ai_bandwidth.csv");
    out_file << "read_write_ratio,aggregate_bandwidth_flits,avg_utilization\n";

    std::vector<double> ratios = {0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0};
    for (double ratio : ratios) {
        Simulator sim;
        if (!sim.init(config_file)) return;

        for (auto* st : sim.stations) {
            auto nodes = sim.node_dir->all_nodes;
            for (const auto& n : nodes) {
                if (n.ring_id == st->ring->ring_id && n.station_id == st->station_id && n.type == "AICORE") {
                    std::vector<std::string> targets = {"LLC", "L2"};
                    auto gen = std::make_unique<HotspotGenerator>(n.ring_id, n.station_id, st, sim.node_dir, targets);
                    sim.traffic_generators.push_back(std::move(gen));
                }
            }
        }

        int warm_up = 1000;
        int sim_cycles = 5000;
        uint64_t total_received = 0;

        for (int i = 0; i < warm_up + sim_cycles; ++i) {
            for (auto& gen : sim.traffic_generators) gen->tick(ratio * 0.5);

            for (auto& comp : sim.components) comp->tick();
            for (auto& comp : sim.components) comp->tock();

            for (auto* st : sim.stations) {
                auto nodes = sim.node_dir->all_nodes;
                for (const auto& n : nodes) {
                    if (n.ring_id == st->ring->ring_id && n.station_id == st->station_id && (n.type == "LLC" || n.type == "L2")) {
                        for (int k = 0; k < 2; ++k) {
                            while (!st->node_if[k].eject_q.q.empty()) {
                                st->node_if[k].eject_q.pop_oldest();
                                if (i >= warm_up) {
                                    total_received++;
                                }
                            }
                        }
                    }
                }
            }
        }

        uint64_t total_active = 0;
        uint64_t total_slots = 0;
        for (auto* r : sim.rings) {
            for (int s = 0; s < r->num_stations; ++s) {
                total_active += r->active_cycles_cw[s];
                total_slots += (warm_up + sim_cycles);
                if (r->bidirectional) {
                    total_active += r->active_cycles_ccw[s];
                    total_slots += (warm_up + sim_cycles);
                }
            }
        }
        double avg_util = total_slots > 0 ? (double)total_active / total_slots : 0;
        double bw = (double)total_received / sim_cycles;
        std::cout << "Ratio: " << ratio << " | BW: " << bw << " | Util: " << avg_util << std::endl;
        out_file << ratio << "," << bw << "," << avg_util << "\n";
    }
    out_file.close();
}

void run_ca_verify(const std::string& config_file) {
    std::cout << "Running CA Verify Experiment..." << std::endl;
    Simulator sim;
    if (!sim.init(config_file)) return;

    sim.trace.init("../../reports/huawei_c_model/ca_trace.json");
    sim.trace.dump_topology(&sim);

    auto* src_station = sim.stations[8];
    for (int i=1; i<=5; ++i) {
        Flit f;
        f.id = 100 + i;
        f.valid = true;
        f.src_ring = 0;
        f.src_node = 8;
        f.dst_ring = 3;
        f.dst_node = 4;
        src_station->node_if[0].inject_q.push(f);
    }

    auto* blocker_station = sim.stations[12 * 3 + 10];
    for (int i=1; i<=10; ++i) {
        Flit f;
        f.id = 200 + i;
        f.valid = true;
        f.src_ring = 3;
        f.src_node = 10;
        f.dst_ring = 3;
        f.dst_node = 8;
        blocker_station->node_if[0].inject_q.push(f);
    }

    int sim_cycles = 50;
    for (int i = 0; i < sim_cycles; ++i) {
        for (auto& comp : sim.components) comp->tick();
        for (auto& comp : sim.components) comp->tock();
        sim.trace.capture_cycle(&sim, i);
    }

    sim.trace.write_json();
    std::cout << "CA Verify trace generated." << std::endl;
}

int main(int argc, char** argv) {
    if (argc < 5) {
        std::cerr << "Usage: " << argv[0] << " --experiment <server|ai|ca_verify> --config <path.yaml>\n";
        return 1;
    }
    std::string experiment = "";
    std::string config_file = "";
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--experiment" && i + 1 < argc) {
            experiment = argv[++i];
        } else if (arg == "--config" && i + 1 < argc) {
            config_file = argv[++i];
        }
    }
    if (experiment == "server") {
        run_server_experiment(config_file);
    } else if (experiment == "ai") {
        run_ai_experiment(config_file);
    } else if (experiment == "ca_verify") {
        run_ca_verify(config_file);
    } else {
        std::cerr << "Unknown experiment\n";
        return 1;
    }
    return 0;
}

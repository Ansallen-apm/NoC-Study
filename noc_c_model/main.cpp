#include <iostream>
#include <fstream>
#include <vector>
#include <list>
#include <sstream>
#include <yaml-cpp/yaml.h>
#include "Router.h"
#include "Config.h"
#include "Routing.h"
#include "Topology.h"

// Global Simulation Time (全域模擬時間)
int sim_time = 0;

int main(int argc, char* argv[]) {
    if (argc < 3) {
        std::cerr << "Usage: " << argv[0] << " <config_file> <trace_file>" << std::endl;
        return 1;
    }

    // 0. 讀取 YAML 配置 (Load YAML Config)
    Config global_config;
    std::string topo_type = "mesh";
    std::string routing_type = "xy";
    try {
        YAML::Node config = YAML::LoadFile(argv[1]);
        if (config["architecture"]) {
            if (config["architecture"]["topology"]) topo_type = config["architecture"]["topology"].as<std::string>();
            if (config["architecture"]["routing"]) routing_type = config["architecture"]["routing"].as<std::string>();
            if (config["architecture"]["width"]) global_config.mesh_width = config["architecture"]["width"].as<int>();
            if (config["architecture"]["height"]) global_config.mesh_height = config["architecture"]["height"].as<int>();
            if (config["architecture"]["buffer_size"]) global_config.buffer_size = config["architecture"]["buffer_size"].as<int>();
            if (config["architecture"]["frequency_mhz"]) global_config.frequency_mhz = config["architecture"]["frequency_mhz"].as<int>();
            if (config["architecture"]["flit_width_bits"]) global_config.flit_width_bits = config["architecture"]["flit_width_bits"].as<int>();

            if (topo_type == "ring") {
                global_config.num_nodes = global_config.mesh_width;
                global_config.mesh_height = 1;
            } else {
                global_config.num_nodes = global_config.mesh_width * global_config.mesh_height;
            }
        }
    } catch (const YAML::Exception& e) {
        std::cerr << "Error parsing YAML file: " << e.what() << "\nUsing default configuration." << std::endl;
    }

    std::cout << "Configured " << topo_type << ": " << global_config.mesh_width << "x" << global_config.mesh_height << std::endl;

    // 1. Instantiating Interfaces (實例化抽象介面)
    Topology* topology = nullptr;
    RoutingAlgorithm* routing = nullptr;

    if (topo_type == "mesh") {
        topology = new MeshTopology(global_config.mesh_width, global_config.mesh_height);
    } else if (topo_type == "torus") {
        topology = new TorusTopology(global_config.mesh_width, global_config.mesh_height);
    } else if (topo_type == "ring") {
        topology = new RingTopology(global_config.num_nodes);
    } else {
        std::cerr << "Unsupported topology: " << topo_type << std::endl;
        return 1;
    }

    if (topo_type == "ring") {
        routing = new RingRouting(global_config.num_nodes);
    } else {
        routing = new XYRouting(global_config.mesh_width, global_config.mesh_height); // Default to XY for mesh
    }

    // 2. Setup Routers & Network (建立路由器與網路)
    std::vector<Router*> routers;
    for (int i = 0; i < global_config.num_nodes; ++i) {
        routers.push_back(new Router(i, topology->get_max_ports(), global_config.buffer_size, routing));
    }

    topology->build_network(routers);

    // 3. Read Trace (讀取 Trace)
    // We store pending packets in a list. In a real sim, these would have timestamps.
    // Here we assume they are ready to be injected immediately.
    // 我們將待處理的封包儲存在列表中。真實模擬中，這些封包會有時間戳記。
    std::list<Packet> pending_packets;
    std::ifstream infile(argv[2]);
    std::string line;
    while (std::getline(infile, line)) {
        if (line.empty() || line[0] == '#') continue;
        std::stringstream ss(line);
        int src, dst, payload, time;
        // Try reading time if available, else default to 0
        if (ss >> src >> dst >> payload) {
            if (!(ss >> time)) time = 0;
            pending_packets.push_back(Packet(src, dst, payload, time));
        }
    }

    size_t total_packets = pending_packets.size();
    std::cout << "Loaded " << total_packets << " packets." << std::endl;

    // 4. Simulation Loop (模擬迴圈)
    size_t total_received = 0;
    int max_cycles = 10000;

    // Attempt to parse max_cycles from yaml to allow longer tests if specified
    try {
        YAML::Node config = YAML::LoadFile(argv[1]);
        if (config["simulation"] && config["simulation"]["sim_cycles"]) {
            max_cycles = config["simulation"]["sim_cycles"].as<int>() + 5000; // Add margin for draining
        }
    } catch (...) {}

    // Deadlock detection variables
    size_t last_total_received = 0;
    int last_progress_cycle = 0;
    bool is_deadlocked = false;
    const int DEADLOCK_THRESHOLD = 500; // Cycles without delivery before declaring deadlock

    for (sim_time = 0; sim_time < max_cycles; ++sim_time) {
        // Injection Phase (注入階段)
        std::vector<bool> injected_this_cycle(global_config.num_nodes, false);
        auto it = pending_packets.begin();
        while (it != pending_packets.end()) {
            Packet& p = *it;
            // Only inject if it's time, and the node hasn't injected yet this cycle
            if (sim_time >= p.creation_time) {
                if (!injected_this_cycle[p.src_id]) {
                    // Try to inject (嘗試注入)
                    if (routers[p.src_id]->inject_packet(p)) {
                        injected_this_cycle[p.src_id] = true;
                        it = pending_packets.erase(it); // Remove if successful (成功則移除)
                    } else {
                        ++it; // Buffer full, try again later
                    }
                } else {
                    ++it; // Node already injected this cycle, try again next cycle
                }
            } else {
                ++it; // Not time yet
            }
        }

        // Check completion (檢查是否完成)
        total_received = 0;
        for (auto r : routers) {
            total_received += r->ejected_packets.size();
        }

        if (total_received == total_packets && pending_packets.empty()) {
            std::cout << "All packets received at cycle " << sim_time << std::endl;
            break;
        }

        // Deadlock Detection Logic (死結偵測邏輯)
        if (total_received > last_total_received) {
            last_total_received = total_received;
            last_progress_cycle = sim_time;
        } else {
            // Check if packets have been injected but none are coming out
            // pending_packets.size() is not zero if there are trace packets left, but in DSE trace drops are massive at cycle 0.
            // We consider the network stalled if time passed threshold since last received and total_received < total_packets.
            if ((sim_time - last_progress_cycle) > DEADLOCK_THRESHOLD && total_received < total_packets) {
                std::cerr << "[DEADLOCK DETECTED] at cycle " << sim_time << "!" << std::endl;
                is_deadlocked = true;
                break;
            }
        }

        // Evaluate all routers (階段一：評估網路狀態)
        for (auto r : routers) {
            r->evaluate(sim_time);
        }

        // Update all routers (階段二：更新緩衝區)
        for (auto r : routers) {
            r->update();
        }
    }

    // 5. Report (報告)
    std::cout << "Simulation finished." << std::endl;
    std::cout << "Total Received: " << total_received << "/" << total_packets << std::endl;

    if (total_received != total_packets) {
        std::cout << "Pending Packets: " << pending_packets.size() << std::endl;
    }

    // Calculate latency and throughput (計算延遲與吞吐量)
    long long total_latency = 0;
    int max_latency = 0;
    for (auto r : routers) {
        for (const auto& p : r->ejected_packets) {
            int lat = p.ejection_time - p.creation_time;
            total_latency += lat;
            if (lat > max_latency) max_latency = lat;
        }
    }

    double avg_latency = total_received > 0 ? (double)total_latency / total_received : 0.0;
    double throughput = sim_time > 0 ? (double)total_received / sim_time : 0.0;

    // Calculate Bandwidth if frequency and flit width are given
    // Throughput (packets/cycle) * Flits/packet * Flit_width (bits) * Frequency (MHz) = Bandwidth (Mbits/s)
    // Assume 1 packet = 1 flit for simplicity in this functional model unless specified otherwise
    double bw_gbps = (throughput * global_config.flit_width_bits * global_config.frequency_mhz) / (8.0 * 1024.0);

    std::cout << "Average Latency: " << avg_latency << " cycles" << std::endl;
    std::cout << "Max Latency: " << max_latency << " cycles" << std::endl;
    std::cout << "Total Throughput: " << throughput << " packets/cycle" << std::endl;
    std::cout << "Total Bandwidth: " << bw_gbps << " GB/s" << std::endl;

    // Dump hardware monitors to JSON report
    std::ofstream out_json("router_stats.json");
    out_json << "{\n";
    out_json << "  \"system_metrics\": {\n";
    out_json << "    \"total_cycles\": " << sim_time << ",\n";
    out_json << "    \"total_packets\": " << total_received << ",\n";
    out_json << "    \"avg_latency\": " << avg_latency << ",\n";
    out_json << "    \"max_latency\": " << max_latency << ",\n";
    out_json << "    \"throughput_pkts_per_cycle\": " << throughput << ",\n";
    out_json << "    \"bandwidth_gbps\": " << bw_gbps << ",\n";
    out_json << "    \"is_deadlock\": " << (is_deadlocked ? "true" : "false") << "\n";
    out_json << "  },\n";
    out_json << "  \"routers\": [\n";
    for (size_t i = 0; i < routers.size(); ++i) {
        auto r = routers[i];
        out_json << "    {\n";
        out_json << "      \"id\": " << r->id << ",\n";
        out_json << "      \"ports\": [\n";
        for (int p = 0; p < r->num_ports; ++p) {
            double uRate = sim_time > 0 ? (double)r->port_active_cycles[p] / sim_time : 0.0;
            double avg_depth = sim_time > 0 ? (double)r->port_buffer_depth_acc[p] / sim_time : 0.0;
            out_json << "        {\n";
            out_json << "          \"port_id\": " << p << ",\n";
            out_json << "          \"uRate\": " << uRate << ",\n";
            out_json << "          \"avg_buffer_depth\": " << avg_depth << ",\n";
            out_json << "          \"max_buffer_depth\": " << r->port_max_buffer_depth[p] << "\n";
            out_json << "        }" << (p == r->num_ports - 1 ? "" : ",") << "\n";
        }
        out_json << "      ]\n";
        out_json << "    }" << (i == routers.size() - 1 ? "" : ",") << "\n";
    }
    out_json << "  ]\n";
    out_json << "}\n";
    out_json.close();

    // Dump specific reception info (輸出特定接收資訊)
    for (auto r : routers) {
        if (!r->ejected_packets.empty()) {
            std::cout << "Router " << r->id << " received: ";
            for (const auto& p : r->ejected_packets) {
                std::cout << "[Src:" << p.src_id << " Data:" << p.payload << " Lat:" << (p.ejection_time - p.creation_time) << "] ";
            }
            std::cout << std::endl;
        }
    }

    // Clean up (清理)
    for (auto r : routers) delete r;
    delete topology;
    delete routing;

    return 0;
}

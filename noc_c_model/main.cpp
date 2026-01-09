#include <iostream>
#include <fstream>
#include <vector>
#include <list>
#include <sstream>
#include "Router.h"
#include "Config.h"

// Global Simulation Time
int sim_time = 0;

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <trace_file>" << std::endl;
        return 1;
    }

    // 1. Setup Mesh
    std::vector<Router*> routers;
    for (int i = 0; i < Config::NUM_NODES; ++i) {
        routers.push_back(new Router(i));
    }

    // Connect Mesh
    for (int y = 0; y < Config::MESH_HEIGHT; ++y) {
        for (int x = 0; x < Config::MESH_WIDTH; ++x) {
            int id = y * Config::MESH_WIDTH + x;
            Router* r = routers[id];

            // North
            if (y > 0) r->connect(NORTH, routers[(y - 1) * Config::MESH_WIDTH + x]);
            // South
            if (y < Config::MESH_HEIGHT - 1) r->connect(SOUTH, routers[(y + 1) * Config::MESH_WIDTH + x]);
            // West
            if (x > 0) r->connect(WEST, routers[y * Config::MESH_WIDTH + (x - 1)]);
            // East
            if (x < Config::MESH_WIDTH - 1) r->connect(EAST, routers[y * Config::MESH_WIDTH + (x + 1)]);
        }
    }

    // 2. Read Trace
    // We store pending packets in a list. In a real sim, these would have timestamps.
    // Here we assume they are ready to be injected immediately.
    std::list<Packet> pending_packets;
    std::ifstream infile(argv[1]);
    std::string line;
    while (std::getline(infile, line)) {
        if (line.empty() || line[0] == '#') continue;
        std::stringstream ss(line);
        int src, dst, payload;
        if (ss >> src >> dst >> payload) {
            pending_packets.push_back(Packet(src, dst, payload, 0));
        }
    }

    size_t total_packets = pending_packets.size();
    std::cout << "Loaded " << total_packets << " packets." << std::endl;

    // 3. Simulation Loop
    size_t total_received = 0;
    int max_cycles = 10000;

    for (sim_time = 0; sim_time < max_cycles; ++sim_time) {
        // Injection Phase
        auto it = pending_packets.begin();
        while (it != pending_packets.end()) {
            Packet& p = *it;
            // Try to inject
            if (routers[p.src_id]->inject_packet(p)) {
                it = pending_packets.erase(it); // Remove if successful
            } else {
                ++it; // Try next packet if this one failed (Head-of-Line blocking at source? Or try others?)
                // For simplicity, we try to inject as many as possible.
                // A real source would probably block.
            }
        }

        // Check completion
        total_received = 0;
        for (auto r : routers) {
            total_received += r->ejected_packets.size();
        }

        if (total_received == total_packets && pending_packets.empty()) {
            std::cout << "All packets received at cycle " << sim_time << std::endl;
            break;
        }

        // Step all routers
        for (auto r : routers) {
            r->step();
        }
    }

    // 4. Report
    std::cout << "Simulation finished." << std::endl;
    std::cout << "Total Received: " << total_received << "/" << total_packets << std::endl;

    if (total_received != total_packets) {
        std::cout << "Pending Packets: " << pending_packets.size() << std::endl;
    }

    // Dump specific reception info
    for (auto r : routers) {
        if (!r->ejected_packets.empty()) {
            std::cout << "Router " << r->id << " received: ";
            for (const auto& p : r->ejected_packets) {
                std::cout << "[Src:" << p.src_id << " Data:" << p.payload << "] ";
            }
            std::cout << std::endl;
        }
    }

    // Clean up
    for (auto r : routers) delete r;

    return 0;
}

#ifndef TRACE_HPP
#define TRACE_HPP

#include <string>
#include <vector>
#include <map>
#include <memory>
#include <fstream>
#include "flit.hpp"

// General Trace format structures
struct TraceLink {
    std::string src_node;
    std::string dst_node;
    bool occupied = false;
    uint64_t flit_id = 0;
};

struct TraceBuffer {
    std::string node_name;
    std::string buffer_name;
    int current_size = 0;
    int capacity = 0;
    std::vector<uint64_t> flit_ids;
};

struct TraceCycle {
    uint64_t cycle;
    std::vector<TraceLink> links;
    std::vector<TraceBuffer> buffers;
};

struct TraceTopologyNode {
    std::string name;
    std::string type; // e.g., "router", "station", "endpoint"
    int x = 0; // layout coordinates
    int y = 0;
};

struct TraceTopologyLink {
    std::string src;
    std::string dst;
    std::string type; // e.g., "ring_cw", "ring_ccw", "bridge", "eject"
};

class Simulator; // Forward declaration

class TraceDumper {
    std::string filepath;
    bool active = false;

    std::vector<TraceTopologyNode> top_nodes;
    std::vector<TraceTopologyLink> top_links;
    std::vector<TraceCycle> cycles;

public:
    TraceDumper() = default;

    void init(const std::string& path) {
        filepath = path;
        active = true;
    }

    bool is_active() const { return active; }

    // Dumps the static topology structure
    void dump_topology(Simulator* sim);

    // Captures the state of the network at the current cycle
    void capture_cycle(Simulator* sim, uint64_t cycle);

    // Writes everything to JSON
    void write_json();
};

#endif // TRACE_HPP

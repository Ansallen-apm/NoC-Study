#ifndef CONFIG_HPP
#define CONFIG_HPP

#include <string>
#include <vector>
#include <optional>

struct RingConfig {
    int id;
    std::string die;
    std::string type;
    int stations;
};

struct NodeConfig {
    int id;
    std::string type;
    int ring;
    int station;
    // For AI Processor
    int count_per_ring;
};

struct BridgeConfig {
    std::string type;
    int local_ring;
    int remote_ring;
    int local_station;
    int remote_station;
    int d2d_latency_cycles;
};

struct MultiRingConfig {
    int count;
    std::string type;
    int stations_per_ring;
};

struct RBRGL1Config {
    bool at_each_intersection = false;
    int queue_depth = 4;
    int latency_cycles = 2;
};

struct RoutingConfig {
    std::string mode;
};

class Config {
public:
    std::string topology;
    int flit_bytes = 0;

    // Server-CPU specific
    std::vector<RingConfig> rings;
    std::vector<NodeConfig> nodes;
    std::vector<BridgeConfig> bridges;

    // AI-Processor specific
    std::optional<MultiRingConfig> vertical_rings;
    std::optional<MultiRingConfig> horizontal_rings;
    std::optional<RBRGL1Config> rbrg_l1;

    std::vector<NodeConfig> vertical_nodes;
    std::vector<NodeConfig> horizontal_nodes;
    std::optional<RoutingConfig> routing;

    bool parse(const std::string& filepath);
};

#endif // CONFIG_HPP

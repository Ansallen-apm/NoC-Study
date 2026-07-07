#ifndef TRAFFIC_GENERATOR_HPP
#define TRAFFIC_GENERATOR_HPP

#include "flit.hpp"
#include "cross_station.hpp"
#include "config.hpp"
#include <vector>
#include <map>
#include <string>
#include <random>
#include <memory>

class NodeDirectory {
public:
    struct NodeInfo {
        int ring_id;
        int station_id;
        std::string type;
    };

    std::vector<NodeInfo> all_nodes;
    std::map<std::string, std::vector<NodeInfo>> nodes_by_type;

    void add_node(int r_id, int s_id, const std::string& type) {
        NodeInfo info{r_id, s_id, type};
        all_nodes.push_back(info);
        nodes_by_type[type].push_back(info);
    }

    std::vector<NodeInfo> get_nodes_by_type(const std::string& type) const {
        auto it = nodes_by_type.find(type);
        if (it != nodes_by_type.end()) return it->second;
        return {};
    }
};

class TrafficGenerator {
protected:
    int src_ring;
    int src_station;
    CrossStation* attached_station;
    std::shared_ptr<NodeDirectory> directory;
    std::mt19937 rng;
    uint64_t flit_id_counter = 0;

public:
    TrafficGenerator(int s_ring, int s_station, CrossStation* station, std::shared_ptr<NodeDirectory> dir, int seed = 42)
        : src_ring(s_ring), src_station(s_station), attached_station(station), directory(dir), rng(seed) {}

    virtual ~TrafficGenerator() = default;

    virtual void tick(double injection_rate) = 0;
};

class HotspotGenerator : public TrafficGenerator {
    std::vector<std::string> target_types;
public:
    HotspotGenerator(int s_ring, int s_station, CrossStation* station, std::shared_ptr<NodeDirectory> dir, const std::vector<std::string>& targets, int seed = 42)
        : TrafficGenerator(s_ring, s_station, station, dir, seed), target_types(targets) {}

    void tick(double injection_rate) override;
};

#endif // TRAFFIC_GENERATOR_HPP

#ifndef SIMULATOR_HPP
#define SIMULATOR_HPP

#include "config.hpp"
#include "stats.hpp"
#include "trace.hpp"
#include "component.hpp"
#include "traffic_generator.hpp"
#include "rbrg_l1.hpp"
#include "rbrg_l2.hpp"
#include "router.hpp"
#include <vector>
#include <memory>

class Ring;
class CrossStation;

class Simulator {
public:
    Config config;
    StatCollector stats;
    TraceDumper trace;

    std::vector<std::unique_ptr<Component>> components;
    std::vector<Ring*> rings;
    std::vector<CrossStation*> stations;

    std::vector<std::unique_ptr<TrafficGenerator>> traffic_generators;
    std::shared_ptr<NodeDirectory> node_dir;
    std::shared_ptr<Router> global_router;

    bool init(const std::string& config_path);
    void build_from_config();
    void run(uint64_t cycles);

    void add_component(std::unique_ptr<Component> comp);
    void init_topology();

private:
    void instantiate_server_cpu();
    void instantiate_ai_processor();
};

#endif // SIMULATOR_HPP

#ifndef SIMULATOR_HPP
#define SIMULATOR_HPP

#include "config.hpp"
#include "stats.hpp"
#include "trace.hpp"
#include "component.hpp"
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
    std::vector<Ring*> rings; // Keep raw pointers for quick access, owned by components
    std::vector<CrossStation*> stations;

    bool init(const std::string& config_path);
    void run(uint64_t cycles);

    void add_component(std::unique_ptr<Component> comp);
    void init_topology();

private:
    void instantiate_server_cpu();
    void instantiate_ai_processor();
};

#endif // SIMULATOR_HPP

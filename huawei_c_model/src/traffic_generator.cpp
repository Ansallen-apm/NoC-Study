#include "simulator.hpp"
#include "traffic_generator.hpp"

void HotspotGenerator::tick(double injection_rate) {
    std::uniform_real_distribution<double> dist(0.0, 1.0);
    if (dist(rng) < injection_rate) {
        if (target_types.empty()) return;

        std::uniform_int_distribution<int> type_dist(0, target_types.size() - 1);
        std::string chosen_type = target_types[type_dist(rng)];

        auto candidates = directory->get_nodes_by_type(chosen_type);
        if (candidates.empty()) return;

        std::uniform_int_distribution<int> node_dist(0, candidates.size() - 1);
        auto target = candidates[node_dist(rng)];

        for (int k = 0; k < 2; ++k) {
            if (attached_station->node_if[k].inject_q.can_push()) {
                Flit f;
                f.id = ++flit_id_counter;
                f.valid = true;
                f.src_ring = src_ring;
                f.src_node = src_station;
                f.dst_ring = target.ring_id;
                f.dst_node = target.station_id;
                f.dir = attached_station->choose_direction(f.src_node, f.dst_node, attached_station->ring->num_stations);
                f.create_cycle = (attached_station->sim_ptr) ? attached_station->sim_ptr->stats.total_cycles : 0;

                attached_station->node_if[k].inject_q.push(f);
                break;
            }
        }
    }
}

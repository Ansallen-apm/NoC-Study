#ifndef RBRG_L1_HPP
#define RBRG_L1_HPP

#include "component.hpp"
#include "ring.hpp"
#include "node_interface.hpp"
#include "config.hpp"
#include "router.hpp"
#include <memory>
#include <queue>
#include <vector>

class RBRG_L1 : public Component {
public:
    int local_ring_id;
    int local_station_id;
    int remote_ring_id;
    int remote_station_id;

    int latency_cycles;
    int queue_depth;

    Ring* local_ring = nullptr;
    Ring* remote_ring = nullptr;
    std::shared_ptr<Router> router;

    // Queues
    std::deque<Flit> ingress_queue; // from local ring
    std::deque<Flit> egress_queue;  // to remote ring

    // Pipeline registers for delay modeling
    struct PipelineStage {
        bool valid = false;
        Flit flit;
    };
    std::vector<PipelineStage> pipeline_regs_curr;
    std::vector<PipelineStage> pipeline_regs_next;

    RBRG_L1(int l_ring, int l_station, int r_ring, int r_station, const RBRGL1Config& config, std::shared_ptr<Router> router_ptr);

    void set_local_ring(Ring* r) { local_ring = r; }
    void set_remote_ring(Ring* r) { remote_ring = r; }

    void tick() override;
    void tock() override;
};

#endif // RBRG_L1_HPP

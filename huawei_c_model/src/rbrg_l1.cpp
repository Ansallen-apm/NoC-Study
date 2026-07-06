#include "rbrg_l1.hpp"
#include <cassert>

RBRG_L1::RBRG_L1(int l_ring, int l_station, int r_ring, int r_station, const RBRGL1Config& config, std::shared_ptr<Router> router_ptr)
    : local_ring_id(l_ring), local_station_id(l_station),
      remote_ring_id(r_ring), remote_station_id(r_station),
      latency_cycles(config.latency_cycles), queue_depth(config.queue_depth),
      router(router_ptr) {
    assert(latency_cycles > 0 && "RBRG_L1 latency_cycles must be > 0");

    // pipeline stages = latency_cycles
    pipeline_regs_curr.resize(latency_cycles);
    pipeline_regs_next.resize(latency_cycles);
}

void RBRG_L1::tick() {
    assert(local_ring != nullptr && remote_ring != nullptr);

    // Initialize next state with current state
    pipeline_regs_next = pipeline_regs_curr;

    // Stage 0: Eject from local ring if router says so and queue has space
    auto& local_slot = local_ring->curr_cw_slots[local_station_id];
    if (local_slot.occupied) {
        if (router->should_forward_to_ring(local_slot.flit, remote_ring_id)) {
            if (ingress_queue.size() < static_cast<size_t>(queue_depth)) {
                // Eject
                ingress_queue.push_back(local_slot.flit);
                local_ring->next_cw_slots[local_station_id].occupied = false;
            }
        }
    }

    // Process pipeline back to front to handle stalls
    // Move from pipeline last stage to egress queue
    if (pipeline_regs_curr[latency_cycles - 1].valid) {
        if (egress_queue.size() < static_cast<size_t>(queue_depth)) {
            egress_queue.push_back(pipeline_regs_curr[latency_cycles - 1].flit);
            pipeline_regs_next[latency_cycles - 1].valid = false;
        }
    }

    // Pipeline progression (Stage 1 to N-1) with stall logic
    for (int i = latency_cycles - 1; i > 0; --i) {
        // If current stage is empty or moving out, we can pull from previous
        if (!pipeline_regs_next[i].valid) {
            if (pipeline_regs_curr[i - 1].valid) {
                pipeline_regs_next[i] = pipeline_regs_curr[i - 1];
                pipeline_regs_next[i - 1].valid = false; // Mark previous as moved
            }
        }
    }

    // Move from ingress to pipeline stage 0
    if (!pipeline_regs_next[0].valid && !ingress_queue.empty()) {
        pipeline_regs_next[0].valid = true;
        pipeline_regs_next[0].flit = ingress_queue.front();
        ingress_queue.pop_front();
    }

    // Stage Final: Inject from egress queue to remote ring
    auto& remote_slot = remote_ring->curr_cw_slots[remote_station_id];
    if (!remote_slot.occupied && !egress_queue.empty()) {
        // Slot is empty, inject!
        remote_ring->next_cw_slots[remote_station_id].occupied = true;
        remote_ring->next_cw_slots[remote_station_id].flit = egress_queue.front();
        egress_queue.pop_front();
    }
}

void RBRG_L1::tock() {
    pipeline_regs_curr = pipeline_regs_next;
}

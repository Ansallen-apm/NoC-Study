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

    pipeline_regs_next = pipeline_regs_curr;

    // Eject from local ring (check CW then CCW)
    auto check_and_eject = [&](auto& curr_slots, auto& next_slots) {
        auto& slot = curr_slots[local_station_id];
        if (slot.occupied && router->should_forward_to_ring(slot.flit, remote_ring_id)) {
            if (ingress_queue.size() < static_cast<size_t>(queue_depth)) {
                ingress_queue.push_back(slot.flit);
                next_slots[local_station_id].occupied = false;
            }
        }
    };
    check_and_eject(local_ring->curr_cw_slots, local_ring->next_cw_slots);
    if (local_ring->bidirectional) {
        check_and_eject(local_ring->curr_ccw_slots, local_ring->next_ccw_slots);
    }

    // Move from pipeline last stage to egress queue
    if (pipeline_regs_curr[latency_cycles - 1].valid) {
        if (egress_queue.size() < static_cast<size_t>(queue_depth)) {
            egress_queue.push_back(pipeline_regs_curr[latency_cycles - 1].flit);
            pipeline_regs_next[latency_cycles - 1].valid = false;
        }
    }

    // Pipeline progression (Stage 1 to N-1) with stall logic
    for (int i = latency_cycles - 1; i > 0; --i) {
        if (!pipeline_regs_next[i].valid) {
            if (pipeline_regs_curr[i - 1].valid) {
                pipeline_regs_next[i] = pipeline_regs_curr[i - 1];
                pipeline_regs_next[i - 1].valid = false;
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
    // We should choose CW or CCW. For simplicity, if bidir, choose shortest path (left as future optimization, just inject CW for now or whichever is empty)
    if (!egress_queue.empty()) {
        if (!remote_ring->next_cw_slots[remote_station_id].occupied) {
            remote_ring->next_cw_slots[remote_station_id].occupied = true;
            remote_ring->next_cw_slots[remote_station_id].flit = egress_queue.front();
            egress_queue.pop_front();
        } else if (remote_ring->bidirectional && !remote_ring->next_ccw_slots[remote_station_id].occupied) {
            remote_ring->next_ccw_slots[remote_station_id].occupied = true;
            remote_ring->next_ccw_slots[remote_station_id].flit = egress_queue.front();
            egress_queue.pop_front();
        }
    }
}

void RBRG_L1::tock() {
    pipeline_regs_curr = pipeline_regs_next;
}

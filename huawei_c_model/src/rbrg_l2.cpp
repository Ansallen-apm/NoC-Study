#include "rbrg_l2.hpp"
#include <cassert>

RBRG_L2::RBRG_L2(int l_ring, int l_station, int r_ring, int r_station,
                 const BridgeConfig& config, int q_depth, int c_depth,
                 std::shared_ptr<Router> router_ptr)
    : local_ring_id(l_ring), local_station_id(l_station),
      remote_ring_id(r_ring), remote_station_id(r_station),
      d2d_latency_cycles(config.d2d_latency_cycles),
      queue_depth(q_depth), initial_credits(c_depth), current_credits(c_depth),
      router(router_ptr) {

    assert(d2d_latency_cycles > 0 && "D2D latency must be > 0");

    d2d_pipeline_curr.resize(d2d_latency_cycles);
    d2d_pipeline_next.resize(d2d_latency_cycles);

    credit_pipeline_curr.resize(d2d_latency_cycles, false);
    credit_pipeline_next.resize(d2d_latency_cycles, false);
}

void RBRG_L2::tick() {
    assert(local_ring != nullptr && remote_ring != nullptr);

    d2d_pipeline_next = d2d_pipeline_curr;
    credit_pipeline_next = credit_pipeline_curr;

    bool credit_returned_this_cycle = false;

    // --- REMOTE DIE (Die 1) LOGIC ---
    // Inject from remote_rx_queue into Remote Ring
    if (!remote_rx_queue.empty()) {
        if (!remote_ring->next_cw_slots[remote_station_id].occupied) {
            remote_ring->next_cw_slots[remote_station_id].occupied = true;
            remote_ring->next_cw_slots[remote_station_id].flit = remote_rx_queue.front();
            remote_rx_queue.pop_front();
            credit_returned_this_cycle = true;
        } else if (remote_ring->bidirectional && !remote_ring->next_ccw_slots[remote_station_id].occupied) {
            remote_ring->next_ccw_slots[remote_station_id].occupied = true;
            remote_ring->next_ccw_slots[remote_station_id].flit = remote_rx_queue.front();
            remote_rx_queue.pop_front();
            credit_returned_this_cycle = true;
        }
    }

    // Receive from D2D Pipeline to remote_rx_queue
    if (d2d_pipeline_curr[d2d_latency_cycles - 1].valid) {
        if (remote_rx_queue.size() < static_cast<size_t>(queue_depth)) {
            remote_rx_queue.push_back(d2d_pipeline_curr[d2d_latency_cycles - 1].flit);
            d2d_pipeline_next[d2d_latency_cycles - 1].valid = false;
        }
    }

    // --- D2D PIPELINES (Flits & Credits) ---
    for (int i = d2d_latency_cycles - 1; i > 0; --i) {
        if (!d2d_pipeline_next[i].valid && d2d_pipeline_curr[i - 1].valid) {
            d2d_pipeline_next[i] = d2d_pipeline_curr[i - 1];
            d2d_pipeline_next[i - 1].valid = false;
        }
    }

    for (int i = d2d_latency_cycles - 1; i > 0; --i) {
        credit_pipeline_next[i] = credit_pipeline_curr[i - 1];
    }
    credit_pipeline_next[0] = credit_returned_this_cycle;

    // --- LOCAL DIE (Die 0) LOGIC ---
    if (credit_pipeline_curr[d2d_latency_cycles - 1]) {
        current_credits++;
    }

    if (!d2d_pipeline_next[0].valid && current_credits > 0) {
        if (!reserved_tx_buffer.empty()) {
            d2d_pipeline_next[0].valid = true;
            d2d_pipeline_next[0].flit = reserved_tx_buffer.front();
            reserved_tx_buffer.pop_front();
            current_credits--;
        } else if (!local_rx_queue.empty()) {
            d2d_pipeline_next[0].valid = true;
            d2d_pipeline_next[0].flit = local_rx_queue.front();
            local_rx_queue.pop_front();
            current_credits--;
        }
    }

    // Eject from Local Ring to local_rx_queue
    auto check_and_eject = [&](auto& curr_slots, auto& next_slots) {
        auto& slot = curr_slots[local_station_id];
        if (slot.occupied && router->should_forward_to_ring(slot.flit, remote_ring_id)) {
            if (local_rx_queue.size() < static_cast<size_t>(queue_depth)) {
                local_rx_queue.push_back(slot.flit);
                next_slots[local_station_id].occupied = false;
            }
        }
    };

    check_and_eject(local_ring->curr_cw_slots, local_ring->next_cw_slots);
    if (local_ring->bidirectional) {
        check_and_eject(local_ring->curr_ccw_slots, local_ring->next_ccw_slots);
    }
}

void RBRG_L2::tock() {
    d2d_pipeline_curr = d2d_pipeline_next;
    credit_pipeline_curr = credit_pipeline_next;
}

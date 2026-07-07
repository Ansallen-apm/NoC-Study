
#include "cross_station.hpp"

CrossStation::CrossStation(int id, Ring* r) : station_id(id), ring(r) {
    node_if.resize(2); // Two node interfaces per cross station

    if (ring->bidirectional) {

    }
}

Direction CrossStation::choose_direction(int src_pos, int dst_pos, int ring_size) {
    int cw_dist = (dst_pos - src_pos + ring_size) % ring_size;
    int ccw_dist = (src_pos - dst_pos + ring_size) % ring_size;
    return cw_dist <= ccw_dist ? Direction::CW : Direction::CCW;
}

int CrossStation::choose_inject_port(Direction dir) {
    for (int k = 0; k < 2; ++k) {
        int port = (rr_ptr + k) % 2;
        if (node_if[port].inject_q.can_pop()) {
            // Check if the flit actually wants to go in the current direction
            // before we consume the round-robin pointer.
            if (node_if[port].inject_q.front().dir == dir || !ring->bidirectional) {
                rr_ptr = (port + 1) % 2;
                return port;
            }
        }
    }
    return -1;
}

void CrossStation::process_direction(const std::vector<RingSlot>& curr_slots, std::vector<RingSlot>& station_outputs, Direction dir, bool wanted_to_inject, bool& injection_failed) {
    const RingSlot& incoming_slot = curr_slots[station_id];

    RingSlot& outgoing_slot = station_outputs[station_id];

    outgoing_slot.e_tag = incoming_slot.e_tag;
    outgoing_slot.e_tag_owner_station = incoming_slot.e_tag_owner_station;
    outgoing_slot.e_tag_flit_id = incoming_slot.e_tag_flit_id;

    // DRM SWAP Evaluation before normal rules
    bool swap_executed = false;
    if (drm_active && swap_sink != nullptr) {
        if (incoming_slot.occupied) {
            Flit f = incoming_slot.flit;
            if (f.dst_node == station_id || f.dst_node == -1) {
                // Find if any eject Q is full and we want to swap
                for (int k = 0; k < 2; ++k) {
                    if (node_if[k].eject_q.is_full() && swap_sink->can_accept_swap() && node_if[k].inject_q.can_pop()) {
                        // SWAP Execution!
                        // 1. Move oldest flit from eject Q to swap sink
                        Flit victim = node_if[k].eject_q.pop_oldest();
                        swap_sink->accept_swap(victim);

                        // 2. Eject traversing flit into newly freed eject Q space
                        f.eject_cycle = f.hop_count;
                        node_if[k].eject_q.push(f);
                        if (incoming_slot.e_tag && incoming_slot.e_tag_flit_id == f.id) {
                            outgoing_slot.e_tag = false;
                        }

                        // 3. Inject waiting flit from inject Q into the slot
                        Flit injecting = node_if[k].inject_q.front();
                        node_if[k].inject_q.pop();

                        outgoing_slot.occupied = true;
                        outgoing_slot.flit = injecting;
                        swap_executed = true;
                        break;
                    }
                }
            }
        }
    }

    if (swap_executed) {
        // I-tag transfer
        outgoing_slot.i_tag = incoming_slot.i_tag;
        outgoing_slot.i_tag_owner_station = incoming_slot.i_tag_owner_station;
        outgoing_slot.i_tag_flit_id = incoming_slot.i_tag_flit_id;
        return; // SWAP handles both eject and inject this cycle!
    }


    if (incoming_slot.occupied) {
        Flit f = incoming_slot.flit;
        if (f.dst_node == station_id || f.dst_node == -1) {
            bool ejected = false;
            for (int k = 0; k < 2; ++k) {
                if (node_if[k].eject_q.is_reserved_for(f.id) || node_if[k].eject_q.has_space()) {
                    f.eject_cycle = f.hop_count;
                    node_if[k].eject_q.push(f);
                    ejected = true;
                    if (incoming_slot.e_tag && incoming_slot.e_tag_flit_id == f.id) {
                        outgoing_slot.e_tag = false;
                    }
                    break;
                }
            }

            if (ejected) {
                outgoing_slot.occupied = false;
            } else {
                f.deflect_count++;
                if (!incoming_slot.e_tag) {
                    for (int k = 0; k < 2; ++k) {
                        if (node_if[k].eject_q.can_reserve()) {
                            node_if[k].eject_q.reserve(f.id);
                            outgoing_slot.e_tag = true;
                            outgoing_slot.e_tag_owner_station = station_id;
                            outgoing_slot.e_tag_flit_id = f.id;
                            break;
                        }
                    }
                }
                outgoing_slot.occupied = true;
                outgoing_slot.flit = f;
            }
        } else {
            outgoing_slot.occupied = true;
            outgoing_slot.flit = f;
            outgoing_slot.flit.hop_count++;
        }
    } else {
        outgoing_slot.occupied = false;
    }

    outgoing_slot.i_tag = incoming_slot.i_tag;
    outgoing_slot.i_tag_owner_station = incoming_slot.i_tag_owner_station;
    outgoing_slot.i_tag_flit_id = incoming_slot.i_tag_flit_id;

    bool injected = false;

    if (!outgoing_slot.occupied) {
        if (!incoming_slot.i_tag) {
            int port = choose_inject_port(dir);
            if (port != -1) {
                Flit injecting = node_if[port].inject_q.front();
                outgoing_slot.occupied = true;
                outgoing_slot.flit = injecting;
                node_if[port].inject_q.pop();
                injected = true;
            }
        } else if (incoming_slot.i_tag_owner_station == station_id) {
            int owner_port = -1;
            for (int k = 0; k < 2; ++k) {
                if (node_if[k].inject_q.can_pop() && node_if[k].inject_q.front().id == incoming_slot.i_tag_flit_id) {
                    owner_port = k;
                    break;
                }
            }
            if (owner_port != -1) {
                Flit injecting = node_if[owner_port].inject_q.front();
                outgoing_slot.occupied = true;
                outgoing_slot.flit = injecting;
                outgoing_slot.i_tag = false;
                node_if[owner_port].inject_q.pop();
                injected = true;
            } else {
                outgoing_slot.i_tag = false;
            }
        }
    }

    if (!injected && wanted_to_inject) {
        injection_failed = true;
        // Output slot is occupied by on-the-fly flit.
        int port = choose_inject_port(dir);
        if (port != -1 && !outgoing_slot.i_tag) {
            Flit injecting = node_if[port].inject_q.front();
            outgoing_slot.i_tag = true;
            outgoing_slot.i_tag_owner_station = station_id;
            outgoing_slot.i_tag_flit_id = injecting.id;
        }
    }
}

void CrossStation::tick() {
    bool injection_failed_this_cycle = false;
    bool wanted_to_inject = false;

    // Check if we want to inject anything
    for (int k = 0; k < 2; ++k) {
        if (node_if[k].inject_q.can_pop()) {
            wanted_to_inject = true;
            break;
        }
    }

    process_direction(ring->curr_cw_slots, ring->next_cw_slots, Direction::CW, wanted_to_inject, injection_failed_this_cycle);

    if (ring->bidirectional) {
        process_direction(ring->curr_ccw_slots, ring->next_ccw_slots, Direction::CCW, wanted_to_inject, injection_failed_this_cycle);
    }

    // Deadlock detection and SWAP

    if (wanted_to_inject && injection_failed_this_cycle) {
        consecutive_inject_fail_cycles++;
    } else {
        consecutive_inject_fail_cycles = 0;
    }

    if (consecutive_inject_fail_cycles > deadlock_threshold_cycles) {
        drm_active = true;
    }

    // If DRM is active, we try to exit if tx buffer clears (handled by swap sink capacity indirectly)
    // Actually DRM exit logic: exit when we inject or when reserved buffer drops below threshold.
    // We'll keep it active as long as we fail, and deactivate when we succeed or threshold drops.
    if (drm_active && consecutive_inject_fail_cycles == 0) {
        drm_active = false;
    }
}

void CrossStation::tock() {}

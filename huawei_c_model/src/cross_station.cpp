#include "cross_station.hpp"

CrossStation::CrossStation(int id, Ring* r) : station_id(id), ring(r) {
    node_if.resize(2); // Two node interfaces per cross station
    next_cw_out.resize(ring->num_stations);
    if (ring->bidirectional) {
        next_ccw_out.resize(ring->num_stations);
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

void CrossStation::process_direction(const std::vector<RingSlot>& curr_slots, std::vector<RingSlot>& station_outputs, Direction dir) {
    const RingSlot& incoming_slot = curr_slots[station_id];
    RingSlot& outgoing_slot = station_outputs[station_id];

    // Transfer E-tag unconditionally initially, might be overridden or cleared
    outgoing_slot.e_tag = incoming_slot.e_tag;
    outgoing_slot.e_tag_owner_station = incoming_slot.e_tag_owner_station;
    outgoing_slot.e_tag_flit_id = incoming_slot.e_tag_flit_id;

    // Priority Rule implementation:
    // 1. On-the-fly flit gets highest priority
    if (incoming_slot.occupied) {
        Flit f = incoming_slot.flit; // Copy to manipulate
        if (f.dst_node == station_id || f.dst_node == -1) { // Assuming dst_node corresponds to station_id for simple test
            // 2. Incoming reaches dest, EjectQueue has space (or we have a reservation!)
            bool ejected = false;
            for (int k = 0; k < 2; ++k) {
                if (node_if[k].eject_q.is_reserved_for(f.id) || node_if[k].eject_q.has_space()) {
                    f.eject_cycle = f.hop_count; // Simplified timing for now
                    // Push handles clearing reservation internally
                    node_if[k].eject_q.push(f);
                    ejected = true;
                    // We ejected, so we should clear the e_tag on the moving slot if it matched us
                    if (incoming_slot.e_tag && incoming_slot.e_tag_flit_id == f.id) {
                        outgoing_slot.e_tag = false;
                    }
                    break;
                }
            }

            if (ejected) {
                // Slot becomes empty
                outgoing_slot.occupied = false;
            } else {
                // 3. Dest reached but EjectQueue full (no normal space and no reservation yet) -> deflect (pass-through)
                f.deflect_count++;

                // Attempt to establish an E-tag reservation if the slot doesn't already have one
                if (!incoming_slot.e_tag) {
                    for (int k = 0; k < 2; ++k) {
                        if (node_if[k].eject_q.can_reserve()) {
                            node_if[k].eject_q.reserve(f.id);
                            outgoing_slot.e_tag = true;
                            outgoing_slot.e_tag_owner_station = station_id; // the station the flit is trying to reach
                            outgoing_slot.e_tag_flit_id = f.id;
                            break;
                        }
                    }
                }

                outgoing_slot.occupied = true;
                outgoing_slot.flit = f;
            }
        } else {
            // Not dest -> pass-through
            outgoing_slot.occupied = true;
            outgoing_slot.flit = f;
            outgoing_slot.flit.hop_count++;
        }
    } else {
        outgoing_slot.occupied = false;
    }

    // Transfer I-tag unconditionally initially
    outgoing_slot.i_tag = incoming_slot.i_tag;
    outgoing_slot.i_tag_owner_station = incoming_slot.i_tag_owner_station;
    outgoing_slot.i_tag_flit_id = incoming_slot.i_tag_flit_id;

    // 4. Output slot is empty, process I-tag rules and round-robin injection
    if (!outgoing_slot.occupied) {
        if (!incoming_slot.i_tag) {
            // Free slot, normal round-robin injection
            int port = choose_inject_port(dir);
            if (port != -1) {
                Flit injecting = node_if[port].inject_q.front();
                outgoing_slot.occupied = true;
                outgoing_slot.flit = injecting;
                node_if[port].inject_q.pop();
            }
        } else if (incoming_slot.i_tag_owner_station == station_id) {
            // It is an I-tag reserved for US.
            // WE MUST ONLY inject the flit that owns the tag.
            int owner_port = -1;
            // Find which queue has the owner flit at the front
            for (int k = 0; k < 2; ++k) {
                if (node_if[k].inject_q.can_pop() && node_if[k].inject_q.front().id == incoming_slot.i_tag_flit_id) {
                    owner_port = k;
                    break;
                }
            }

            if (owner_port != -1) {
                // We found the owner! Inject it and consume the tag.
                Flit injecting = node_if[owner_port].inject_q.front();
                outgoing_slot.occupied = true;
                outgoing_slot.flit = injecting;
                outgoing_slot.i_tag = false;
                node_if[owner_port].inject_q.pop();
            } else {
                // The owner flit is not at the front of either queue (maybe dropped?)
                // Clear the tag to prevent it from permanently occupying the ring
                outgoing_slot.i_tag = false;
            }
        }
        // else: I-tag belongs to someone else, do nothing and let it propagate (already transferred above)
    } else {
        // Output slot is occupied by on-the-fly flit.
        // If we wanted to inject but couldn't, we establish an I-tag on this moving slot.
        // We only do this if it doesn't already have an I-tag, to prevent overriding someone else's reservation.
        // NOTE: we need to check if there is an injecting flit WITHOUT consuming the rr_ptr if we just want to look.
        // But for cycle accuracy, actually choosing is fine because it fails.
        // Wait, choose_inject_port increments rr_ptr. That's fine.
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
    process_direction(ring->curr_cw_slots, next_cw_out, Direction::CW);

    if (ring->bidirectional) {
        process_direction(ring->curr_ccw_slots, next_ccw_out, Direction::CCW);
    }
}

void CrossStation::tock() {
    // Publish station output decisions to the ring's next state
    ring->next_cw_slots[station_id] = next_cw_out[station_id];

    if (ring->bidirectional) {
        ring->next_ccw_slots[station_id] = next_ccw_out[station_id];
    }
}

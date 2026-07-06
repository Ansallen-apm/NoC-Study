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

    // Priority Rule implementation:
    // 1. On-the-fly flit gets highest priority
    if (incoming_slot.occupied) {
        Flit f = incoming_slot.flit; // Copy to manipulate
        if (f.dst_node == station_id || f.dst_node == -1) { // Assuming dst_node corresponds to station_id for simple test
            // 2. Incoming reaches dest, EjectQueue has space
            bool ejected = false;
            for (int k = 0; k < 2; ++k) {
                if (node_if[k].eject_q.has_space()) {
                    f.eject_cycle = f.hop_count; // Simplified timing for now
                    // Just pushing to queue immediately in tick for simple skeleton behavior,
                    // a deeper implementation would defer to tock.
                    node_if[k].eject_q.push(f);
                    ejected = true;
                    break;
                }
            }

            if (ejected) {
                // Slot becomes empty
                outgoing_slot.occupied = false;
            } else {
                // 3. Dest reached but EjectQueue full -> deflect (pass-through)
                f.deflect_count++;
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

    // 5. Output slot is empty, round-robin injection
    if (!outgoing_slot.occupied) {
        int port = choose_inject_port(dir);
        if (port != -1) {
            Flit injecting = node_if[port].inject_q.front();
            outgoing_slot.occupied = true;
            outgoing_slot.flit = injecting;
            node_if[port].inject_q.pop();
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

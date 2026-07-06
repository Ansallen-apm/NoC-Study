#include "ring.hpp"

Ring::Ring(int id, int stations, bool bidir)
    : ring_id(id), num_stations(stations), bidirectional(bidir) {
    curr_cw_slots.resize(num_stations);
    next_cw_slots.resize(num_stations);

    if (bidirectional) {
        curr_ccw_slots.resize(num_stations);
        next_ccw_slots.resize(num_stations);
    }
}

void Ring::tick() {
    // Ring doesn't modify state in tick since it reads from CrossStation outputs
}

void Ring::tock() {
    // CW slot movement: what was written to next_cw_slots[i] (by station i)
    // moves to curr_cw_slots[(i + 1) % N]
    std::vector<RingSlot> new_curr_cw(num_stations);
    for (int i = 0; i < num_stations; ++i) {
        int next_idx = (i + 1) % num_stations;
        new_curr_cw[next_idx] = next_cw_slots[i];
    }
    curr_cw_slots = new_curr_cw;

    // CCW slot movement: slot i moves to (i - 1 + N) % N
    if (bidirectional) {
        std::vector<RingSlot> new_curr_ccw(num_stations);
        for (int i = 0; i < num_stations; ++i) {
            int next_idx = (i - 1 + num_stations) % num_stations;
            new_curr_ccw[next_idx] = next_ccw_slots[i];
        }
        curr_ccw_slots = new_curr_ccw;
    }
}

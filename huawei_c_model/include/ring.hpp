#ifndef RING_HPP
#define RING_HPP

#include "component.hpp"
#include "ring_slot.hpp"
#include <vector>

class Ring : public Component {
public:
    int ring_id;
    int num_stations;
    bool bidirectional;

    std::vector<RingSlot> curr_cw_slots;
    std::vector<RingSlot> next_cw_slots;

    std::vector<RingSlot> curr_ccw_slots;
    std::vector<RingSlot> next_ccw_slots;

    std::vector<uint64_t> active_cycles_cw;
    std::vector<uint64_t> active_cycles_ccw;

    Ring(int id, int stations, bool bidir);

    void tick() override;
    void tock() override;
};

#endif // RING_HPP

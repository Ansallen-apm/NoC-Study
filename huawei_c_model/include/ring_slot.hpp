#ifndef RING_SLOT_HPP
#define RING_SLOT_HPP

#include "flit.hpp"

struct RingSlot {
    bool occupied = false;
    Flit flit;

    // I-tag: Injection reservation
    bool i_tag = false;
    int i_tag_owner_station = -1;
    uint64_t i_tag_flit_id = 0;

    // E-tag: Ejection reservation (moving metadata)
    bool e_tag = false;
    int e_tag_owner_station = -1;
    uint64_t e_tag_flit_id = 0;
};

#endif // RING_SLOT_HPP

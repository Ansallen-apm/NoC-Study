#ifndef RING_SLOT_HPP
#define RING_SLOT_HPP

#include "flit.hpp"

struct RingSlot {
    bool occupied = false;
    Flit flit;
};

#endif // RING_SLOT_HPP

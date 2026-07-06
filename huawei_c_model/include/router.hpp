#ifndef ROUTER_HPP
#define ROUTER_HPP

#include "flit.hpp"

class Router {
public:
    virtual ~Router() = default;

    // Returns true if the flit should be forwarded to the connected remote ring
    // target_ring_id is the ID of the remote ring connected to this bridge/router
    virtual bool should_forward_to_ring(const Flit& flit, int target_ring_id) const = 0;
};

// XY or shortest path style routing simplified for multi-ring
class MultiRingRouter : public Router {
public:
    // Basic logic: if the destination ring matches the target_ring_id, forward it
    bool should_forward_to_ring(const Flit& flit, int target_ring_id) const override {
        return flit.dst_ring == target_ring_id;
    }
};

#endif // ROUTER_HPP

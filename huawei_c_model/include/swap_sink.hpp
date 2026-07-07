#ifndef SWAP_SINK_HPP
#define SWAP_SINK_HPP

#include "flit.hpp"

// Interface for resolving deadlocks by moving flits from a full EjectQueue
// to a reserved buffer, allowing same-cycle swap actions.
class SwapSink {
public:
    virtual ~SwapSink() = default;

    // Checks if the sink can accept a swapped flit this cycle
    virtual bool can_accept_swap() const = 0;

    // Pushes the victim flit into the sink's reserved buffer
    virtual void accept_swap(const Flit& f) = 0;
};

#endif // SWAP_SINK_HPP

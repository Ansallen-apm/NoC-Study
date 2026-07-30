#ifndef CROSS_STATION_HPP
#define CROSS_STATION_HPP

#include "component.hpp"
#include "node_interface.hpp"
#include "swap_sink.hpp"
#include "config.hpp"
#include "ring.hpp"
#include <vector>

class CrossStation : public Component {
public:
    class Simulator* sim_ptr = nullptr;
    void set_sim(Simulator* s) { sim_ptr = s; }
public:
    int station_id;
    Ring* ring;

    // Two local devices (e.g. NodeInterface[0] and [1])
    std::vector<NodeInterface> node_if;
    int rr_ptr = 0;
    SwapSink* swap_sink = nullptr;
    int deadlock_threshold_cycles = 64;
    int consecutive_inject_fail_cycles = 0;
    bool drm_active = false;

    void set_swap_sink(SwapSink* sink) { swap_sink = sink; }
    void set_deadlock_threshold(int t) { deadlock_threshold_cycles = t; } // Round-robin pointer for injection arbitration

    CrossStation(int id, Ring* r);

    void tick() override;
    void tock() override;

    // Helper functions
    Direction choose_direction(int src_pos, int dst_pos, int ring_size);
    int choose_inject_port(Direction dir);

private:
    void process_direction(const std::vector<RingSlot>& curr_slots, std::vector<RingSlot>& station_outputs, Direction dir, bool wanted_to_inject, bool& injection_failed);

    // Internal state to hold the decisions made during tick
};

#endif // CROSS_STATION_HPP

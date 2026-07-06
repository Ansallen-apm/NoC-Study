#ifndef CROSS_STATION_HPP
#define CROSS_STATION_HPP

#include "component.hpp"
#include "node_interface.hpp"
#include "ring.hpp"
#include <vector>

class CrossStation : public Component {
public:
    int station_id;
    Ring* ring;

    // Two local devices (e.g. NodeInterface[0] and [1])
    std::vector<NodeInterface> node_if;
    int rr_ptr = 0; // Round-robin pointer for injection arbitration

    CrossStation(int id, Ring* r);

    void tick() override;
    void tock() override;

    // Helper functions
    Direction choose_direction(int src_pos, int dst_pos, int ring_size);
    int choose_inject_port(Direction dir);

private:
    void process_direction(const std::vector<RingSlot>& curr_slots, std::vector<RingSlot>& station_outputs, Direction dir);

    // Internal state to hold the decisions made during tick
    std::vector<RingSlot> next_cw_out;
    std::vector<RingSlot> next_ccw_out;
};

#endif // CROSS_STATION_HPP

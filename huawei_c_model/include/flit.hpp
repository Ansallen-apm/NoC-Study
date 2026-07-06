#ifndef FLIT_HPP
#define FLIT_HPP

#include <cstdint>

enum class FlitType {
    ReadReq,
    WriteReq,
    SnoopReq,
    DataResp,
    CompAck,
    DMARead,
    DMAWrite
};

enum class Direction {
    CW,  // Clockwise
    CCW  // Counter-Clockwise
};

struct Flit {
    uint64_t id = 0;

    int src_node = -1;
    int dst_node = -1;

    int src_ring = -1;
    int dst_ring = -1;
    int current_ring = -1;

    FlitType type = FlitType::ReadReq;
    Direction dir = Direction::CW;

    uint64_t create_cycle = 0;
    uint64_t inject_cycle = 0;
    uint64_t eject_cycle = 0;

    int hop_count = 0;
    int deflect_count = 0;
    int ring_change_count = 0;

    bool valid = false;

    uint32_t txn_id = 0;
    uint32_t qos = 0;
    uint32_t logical_class = 0;
};

#endif // FLIT_HPP

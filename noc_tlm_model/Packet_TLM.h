#ifndef PACKET_TLM_H
#define PACKET_TLM_H

#include <systemc>
#include <tlm>

struct PacketPayload {
    int src_id;
    int dst_id;
    int payload;
};

// We can use the Generic Payload extension mechanism or just assume the data pointer points to this struct.
// For simplicity in this demo, we assume the data ptr of tlm_generic_payload points to PacketPayload.

#endif

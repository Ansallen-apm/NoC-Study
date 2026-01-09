#ifndef ROUTER_TLM_H
#define ROUTER_TLM_H

#include <systemc>
#include <tlm>
#include <tlm_utils/simple_initiator_socket.h>
#include <tlm_utils/simple_target_socket.h>
#include "Packet_TLM.h"

using namespace sc_core;
using namespace tlm;

class Router_TLM : public sc_module {
public:
    // Sockets
    // 5 Targets (Receivers)
    tlm_utils::simple_target_socket<Router_TLM> target_socket[5];
    // 5 Initiators (Senders)
    tlm_utils::simple_initiator_socket<Router_TLM> initiator_socket[5];

    int id;
    int x, y;

    SC_HAS_PROCESS(Router_TLM);
    Router_TLM(sc_module_name name, int _id) : sc_module(name), id(_id) {
        x = id % 4; // Hardcoded width 4 for now
        y = id / 4;

        for (int i = 0; i < 5; ++i) {
            target_socket[i].register_b_transport(this, &Router_TLM::b_transport, i);
        }
    }

    // Blocking transport implementation
    void b_transport(int id, tlm_generic_payload& trans, sc_time& delay) {
        // 1. Receive packet
        PacketPayload* pp = (PacketPayload*)trans.get_data_ptr();

        // 2. Add routing delay
        delay += sc_time(2, SC_NS); // Router processing time

        // 3. Routing Logic
        int out_port = compute_next_hop(pp->dst_id);

        // 4. Forward if not local
        if (out_port != 0) { // Assuming 0 is Local
             // In a real TLM, we would need to clone the transaction or forward it.
             // Forwarding:
             initiator_socket[out_port]->b_transport(trans, delay);
        } else {
             // Eject (Local consume)
             // Log reception
             // printf("Router %d Received Packet from %d\n", id, pp->src_id);
        }
    }

    int compute_next_hop(int dst_id) {
        int dst_x = dst_id % 4;
        int dst_y = dst_id / 4;

        // Port Mapping: 0:Local, 1:N, 2:E, 3:S, 4:W
        if (dst_x > x) return 2; // East
        if (dst_x < x) return 4; // West
        if (dst_y > y) return 3; // South
        if (dst_y < y) return 1; // North
        return 0; // Local
    }
};

#endif

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
    // Sockets (插座)
    // 5 Targets (Receivers) (5 個目標插座 - 接收端)
    tlm_utils::simple_target_socket<Router_TLM> target_socket[5];
    // 5 Initiators (Senders) (5 個啟動器插座 - 發送端)
    tlm_utils::simple_initiator_socket<Router_TLM> initiator_socket[5];

    int id;
    int x, y;

    SC_HAS_PROCESS(Router_TLM);
    Router_TLM(sc_module_name name, int _id) : sc_module(name), id(_id) {
        x = id % 4; // Hardcoded width 4 for now (目前硬編碼寬度為 4)
        y = id / 4;

        for (int i = 0; i < 5; ++i) {
            target_socket[i].register_b_transport(this, &Router_TLM::b_transport, i);
        }
    }

    // Blocking transport implementation (阻塞傳輸實作)
    void b_transport(int id, tlm_generic_payload& trans, sc_time& delay) {
        // 1. Receive packet (接收封包)
        PacketPayload* pp = (PacketPayload*)trans.get_data_ptr();

        // 2. Add routing delay (增加路由延遲)
        delay += sc_time(2, SC_NS); // Router processing time (路由器處理時間)

        // 3. Routing Logic (路由邏輯)
        int out_port = compute_next_hop(pp->dst_id);

        // 4. Forward if not local (若非本地則轉發)
        if (out_port != 0) { // Assuming 0 is Local (假設 0 為本地)
             // In a real TLM, we would need to clone the transaction or forward it.
             // 在真實的 TLM 中，我們需要複製交易或轉發它。
             // Forwarding:
             initiator_socket[out_port]->b_transport(trans, delay);
        } else {
             // Eject (Local consume) (彈出 - 本地消耗)
             // Log reception (記錄接收)
             // printf("Router %d Received Packet from %d\n", id, pp->src_id);
        }
    }

    int compute_next_hop(int dst_id) {
        int dst_x = dst_id % 4;
        int dst_y = dst_id / 4;

        // Port Mapping: 0:Local, 1:N, 2:E, 3:S, 4:W
        // 埠映射：0:本地, 1:北, 2:東, 3:南, 4:西
        if (dst_x > x) return 2; // East (東)
        if (dst_x < x) return 4; // West (西)
        if (dst_y > y) return 3; // South (南)
        if (dst_y < y) return 1; // North (北)
        return 0; // Local (本地)
    }
};

#endif

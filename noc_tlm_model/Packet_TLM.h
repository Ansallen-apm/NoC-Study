#ifndef PACKET_TLM_H
#define PACKET_TLM_H

#include <systemc>
#include <tlm>

// Packet Payload Structure for TLM (TLM 的封包負載結構)
struct PacketPayload {
    int src_id;  // 來源 ID
    int dst_id;  // 目的 ID
    int payload; // 資料負載
};

// We can use the Generic Payload extension mechanism or just assume the data pointer points to this struct.
// 我們可以使用通用負載擴充機制，或直接假設資料指標指向此結構。

#endif

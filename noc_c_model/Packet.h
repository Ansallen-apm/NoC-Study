#ifndef PACKET_H
#define PACKET_H

#include <iostream>

// Packet Structure (封包結構)
struct Packet {
    int src_id;       // 來源 ID
    int dst_id;       // 目的 ID
    int payload;      // 資料負載
    int creation_time;// 建立時間

    Packet(int s = -1, int d = -1, int p = 0, int time = 0)
        : src_id(s), dst_id(d), payload(p), creation_time(time) {}
};

#endif

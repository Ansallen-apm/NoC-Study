#ifndef PACKET_H
#define PACKET_H

#include <iostream>

enum FlitType { HEAD, BODY, TAIL, HEAD_TAIL };

// Flit Structure (微片結構)
struct Flit {
    int src_id;       // 來源節點 ID
    int dst_id;       // 目的節點 ID
    int packet_id;    // 所屬封包 ID
    int flit_id;      // Flit 在封包中的序號
    FlitType type;    // Flit 類型 (HEAD, BODY, TAIL)
    int payload;      // 資料負載
    int creation_time;// 建立時間 (同 Packet 建立時間)
    int ejection_time;// 到達時間
    int vc_id;        // 佔用的虛擬通道 ID

    Flit(int src = -1, int dst = -1, int pkt_id = -1, int f_id = -1, FlitType t = BODY, int p = 0, int time = 0)
        : src_id(src), dst_id(dst), packet_id(pkt_id), flit_id(f_id), type(t), payload(p), creation_time(time), ejection_time(-1), vc_id(0) {}
};

// Packet Structure (僅用於 Trace 注入管理)
struct Packet {
    int id;           // 封包 ID (Global/Trace level)
    int src_id;       // 來源 ID
    int dst_id;       // 目的 ID
    int payload;      // 資料負載
    int creation_time;// 建立時間
    int size;         // 包含幾個 Flits

    Packet(int _id = -1, int s = -1, int d = -1, int p = 0, int time = 0, int _size = 1)
        : id(_id), src_id(s), dst_id(d), payload(p), creation_time(time), size(_size) {}
};

#endif

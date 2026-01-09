#ifndef PACKET_H
#define PACKET_H

#include <iostream>

struct Packet {
    int src_id;
    int dst_id;
    int payload;
    int creation_time;

    Packet(int s = -1, int d = -1, int p = 0, int time = 0)
        : src_id(s), dst_id(d), payload(p), creation_time(time) {}
};

#endif

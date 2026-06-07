#ifndef CONFIG_H
#define CONFIG_H

// System Configuration (系統配置)
struct Config {
    int mesh_width;
    int mesh_height;
    int num_nodes;
    int buffer_size;
    int frequency_mhz;
    int flit_width_bits;
    int num_vcs;
    int packet_size_flits;

    Config() : mesh_width(4), mesh_height(4), num_nodes(16), buffer_size(4), frequency_mhz(1000), flit_width_bits(128), num_vcs(1), packet_size_flits(4) {}
};

#endif

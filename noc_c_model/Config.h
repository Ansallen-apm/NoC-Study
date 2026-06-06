#ifndef CONFIG_H
#define CONFIG_H

// System Configuration (系統配置)
struct Config {
    int mesh_width;
    int mesh_height;
    int num_nodes;
    int buffer_size;

    Config() : mesh_width(4), mesh_height(4), num_nodes(16), buffer_size(4) {}
};

#endif

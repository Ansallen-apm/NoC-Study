#ifndef CONFIG_H
#define CONFIG_H

struct Config {
    static const int MESH_WIDTH = 4;
    static const int MESH_HEIGHT = 4;
    static const int NUM_NODES = MESH_WIDTH * MESH_HEIGHT;
    static const int BUFFER_SIZE = 4;
};

#endif

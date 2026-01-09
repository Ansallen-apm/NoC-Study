#ifndef CONFIG_H
#define CONFIG_H

// System Configuration (系統配置)
struct Config {
    static const int MESH_WIDTH = 4;   // 網格寬度
    static const int MESH_HEIGHT = 4;  // 網格高度
    static const int NUM_NODES = MESH_WIDTH * MESH_HEIGHT; // 總節點數
    static const int BUFFER_SIZE = 4;  // 每個埠的緩衝區大小
};

#endif

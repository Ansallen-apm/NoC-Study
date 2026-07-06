#include <gtest/gtest.h>
#include "config.hpp"

TEST(ConfigTest, ParseServerCPU) {
    Config cfg;
    ASSERT_TRUE(cfg.parse("../configs/server_cpu.yaml"));
    EXPECT_EQ(cfg.topology, "server_cpu");
    EXPECT_EQ(cfg.flit_bytes, 64);
    EXPECT_EQ(cfg.rings.size(), 2);
    EXPECT_EQ(cfg.rings[0].die, "CCD0");
    EXPECT_EQ(cfg.rings[1].type, "half");
    EXPECT_EQ(cfg.nodes.size(), 6);
    EXPECT_EQ(cfg.nodes[0].type, "CPU_CLUSTER");
    EXPECT_EQ(cfg.nodes[5].type, "ETHERNET");
    EXPECT_EQ(cfg.bridges.size(), 1);
    EXPECT_EQ(cfg.bridges[0].type, "RBRG_L2");
}

TEST(ConfigTest, ParseAIProcessor) {
    Config cfg;
    ASSERT_TRUE(cfg.parse("../configs/ai_processor.yaml"));
    EXPECT_EQ(cfg.topology, "ai_processor");
    EXPECT_EQ(cfg.flit_bytes, 64);
    ASSERT_TRUE(cfg.vertical_rings.has_value());
    EXPECT_EQ(cfg.vertical_rings->count, 8);
    ASSERT_TRUE(cfg.horizontal_rings.has_value());
    EXPECT_EQ(cfg.horizontal_rings->type, "half");
    ASSERT_TRUE(cfg.rbrg_l1.has_value());
    EXPECT_TRUE(cfg.rbrg_l1->at_each_intersection);
    EXPECT_EQ(cfg.vertical_nodes.size(), 1);
    EXPECT_EQ(cfg.horizontal_nodes.size(), 3);
    EXPECT_EQ(cfg.horizontal_nodes[1].type, "LLC");
    ASSERT_TRUE(cfg.routing.has_value());
    EXPECT_EQ(cfg.routing->mode, "XY");
}

#include <gtest/gtest.h>
#include "config.hpp"
#include <fstream>
#include <cstdio>

TEST(ConfigTest, ParseServerCPU) {
    Config cfg;
    ASSERT_TRUE(cfg.parse("../configs/server_cpu.yaml"));
    EXPECT_EQ(cfg.topology, "server_cpu");
}

TEST(ConfigTest, ParseAIProcessor) {
    Config cfg;
    ASSERT_TRUE(cfg.parse("../configs/ai_processor.yaml"));
    EXPECT_EQ(cfg.topology, "ai_processor");
}

TEST(ConfigTest, MissingTopologyThrows) {
    std::ofstream out("bad_config1.yaml");
    out << R"(
global:
  frequency_mhz: 1000
)";
    out.close();

    Config cfg;
    EXPECT_FALSE(cfg.parse("bad_config1.yaml"));
    std::remove("bad_config1.yaml");
}

TEST(ConfigTest, MissingRingFieldsThrows) {
    std::ofstream out("bad_config2.yaml");
    out << R"(
topology: custom
rings:
  - id: 0
    # missing type and stations
)";
    out.close();

    Config cfg;
    EXPECT_FALSE(cfg.parse("bad_config2.yaml"));
    std::remove("bad_config2.yaml");
}

TEST(ConfigTest, MissingAINodesThrows) {
    std::ofstream out("bad_config3.yaml");
    out << R"(
topology: ai_processor
nodes:
  vertical:
    - type: AICORE
      # missing count_per_ring
)";
    out.close();

    Config cfg;
    EXPECT_FALSE(cfg.parse("bad_config3.yaml"));
    std::remove("bad_config3.yaml");
}

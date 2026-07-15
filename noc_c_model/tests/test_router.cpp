#include <gtest/gtest.h>
#include "../Router.h"
#include "../Routing.h"
#include "../Topology.h"

// Test harness for router invariants
class RouterInvariantTest : public ::testing::Test {
protected:
    std::vector<std::unique_ptr<Router>> routers;
    std::vector<Router*> raw_routers;
    std::unique_ptr<Topology> topo;
    std::unique_ptr<RoutingAlgorithm> routing;
    int buffer_size = 4;
    int num_vcs = 2;

    void setup_ring(int size) {
        buffer_size = 2; // Reduce buffer size to force credit exhaustion
        topo.reset(new RingTopology(size));
        routing.reset(new RingRouting(size));
        for (int i = 0; i < size; ++i) {
            routers.push_back(std::unique_ptr<Router>(new Router(i, topo->get_max_ports(), num_vcs, buffer_size, routing.get())));
            raw_routers.push_back(routers.back().get());
        }
        topo->build_network(raw_routers);
    }

    int get_total_buffered_flits() {
        int count = 0;
        for (const auto& r : routers) {
            for (int p = 0; p < r->num_ports; ++p) {
                for (int v = 0; v < num_vcs; ++v) {
                    count += r->input_buffers[p][v].size();
                    count += r->next_input_buffers[p][v].size();
                }
            }
        }
        return count;
    }

    int get_total_ejected_flits() {
        int count = 0;
        for (const auto& r : routers) {
            count += r->received_flits;
        }
        return count;
    }
    void setup_torus(int width, int height) {
        buffer_size = 2; // Reduce buffer size to force credit exhaustion
        int size = width * height;
        topo.reset(new TorusTopology(width, height));
        routing.reset(new TorusRouting(width, height));
        for (int i = 0; i < size; ++i) {
            routers.push_back(std::unique_ptr<Router>(new Router(i, topo->get_max_ports(), num_vcs, buffer_size, routing.get())));
            raw_routers.push_back(routers.back().get());
        }
        topo->build_network(raw_routers);
    }
};

TEST_F(RouterInvariantTest, InvariantsAndDateline) {
    setup_ring(5);

    int total_injected = 0;
    std::vector<std::queue<Flit>> source_queues(5);

    // Enqueue lots of flits to cause wrapping and dateline transitions, ensuring multi-hop and congestion.
    // Node 4 to Node 1 (Right/EAST, 4 -> 0 -> 1). Wrap triggers on 4 -> 0 (id > next_id).
    for (int i = 0; i < 12; ++i) {
        Flit f(4, 1, 0, i, (i == 0) ? HEAD : (i == 11 ? TAIL : BODY), 0, 0);
        source_queues[4].push(f);
    }

    // Node 0 to Node 3 (Left/WEST, 0 -> 4 -> 3). Wrap triggers on 0 -> 4 (id < next_id).
    for (int i = 0; i < 12; ++i) {
        Flit f(0, 3, 1, i, (i == 0) ? HEAD : (i == 11 ? TAIL : BODY), 0, 0);
        source_queues[0].push(f);
    }

    int max_cycles = 150; // Enough for 5 nodes to deliver 24 congested flits across multi-hop
    bool saw_vc1 = false;

    for (int cycle = 0; cycle < max_cycles; ++cycle) {
        // Injection Phase
        for (int i = 0; i < 5; ++i) {
            while (!source_queues[i].empty()) {
                Flit f = source_queues[i].front();
                if (routers[i]->inject_flit(f)) {
                    source_queues[i].pop();
                    total_injected++;
                } else {
                    break;
                }
            }
        }

        for (const auto& r : routers) r->evaluate(cycle);
        for (const auto& r : routers) r->update();

        // Check Credit Conservation for every router, port, and VC
        for (const auto& r : routers) {
            for (int out_port = 1; out_port < r->num_ports; ++out_port) {
                Router* next_r = r->neighbors[out_port];
                int ingress_port = r->neighbor_ingress_ports[out_port];
                if (next_r) {
                    for (int v = 0; v < num_vcs; ++v) {
                        int current_credits = r->downstream_credits[out_port][v];
                        int receiving_buffer_occupancy = next_r->input_buffers[ingress_port][v].size();

                        EXPECT_GE(current_credits, 0) << "Credits went negative at Router " << r->id << " port " << out_port << " VC " << v;
                        EXPECT_EQ(current_credits + receiving_buffer_occupancy, buffer_size)
                            << "Credit invariant violated at Router " << r->id << " -> Router " << next_r->id;
                    }
                }
            }
        }

        // Check Flit Conservation
        int buffered = get_total_buffered_flits();
        int ejected = get_total_ejected_flits();
        EXPECT_EQ(total_injected, buffered + ejected) << "Flit conservation violated at cycle " << cycle;

        // Check Dateline One-Directionality
        // We know new flits are injected at VC 0. Once they wrap, they bump to VC 1.
        // There is no mechanism to downgrade VC, so flits in buffers must be VC 0 or 1.
        for (const auto& r : routers) {
            for (int p = 0; p < r->num_ports; ++p) {
                for (int v = 0; v < num_vcs; ++v) {
                    // Make a copy of the queue to inspect it without popping the real one
                    std::queue<Flit> q = r->input_buffers[p][v];
                    while (!q.empty()) {
                        Flit f = q.front();
                        q.pop();
                        // f.vc_id should be equal to the queue it resides in
                        EXPECT_EQ(f.vc_id, v) << "Flit is in VC " << v << " queue but its internal vc_id is " << f.vc_id;
                        // For this specific test, we know it's injected at VC0, so if it's in VC1, it got bumped.
                        EXPECT_GE(f.vc_id, 0);
                        EXPECT_LE(f.vc_id, 1);

                        if (f.vc_id == 1) {
                            saw_vc1 = true;
                        }
                    }
                }
            }
        }
    }

    // Ensure all queued flits were actually injected
    EXPECT_EQ(total_injected, 24);

    // By the end, all flits should be delivered
    EXPECT_EQ(get_total_ejected_flits(), total_injected) << "Not all flits were delivered in time.";

    // Explicitly assert that at least one flit was bumped to VC 1 due to wraparound
    EXPECT_TRUE(saw_vc1) << "Dateline wrap did not result in any flits being bumped to VC 1!";
}

TEST_F(RouterInvariantTest, TorusInvariants) {
    setup_torus(3, 3);

    int total_injected = 0;
    std::vector<std::queue<Flit>> source_queues(9);

    // Enqueue flits for X -> Y dimension routing causing a VC reset
    // Node 0 (0,0) to Node 5 (2,1). Path: 0 -> 2 (Wrap X) -> 5 (Down Y).
    // X distance is 1 (left wrap), Y distance is 1 (down).
    for (int i = 0; i < 12; ++i) {
        Flit f(0, 5, 0, i, (i == 0) ? HEAD : (i == 11 ? TAIL : BODY), 0, 0);
        source_queues[0].push(f);
    }

    // Node 8 (2,2) to Node 3 (0,1). Path: 8 -> 6 (Wrap X) -> 3 (Up Y Wrap).
    for (int i = 0; i < 12; ++i) {
        Flit f(8, 3, 1, i, (i == 0) ? HEAD : (i == 11 ? TAIL : BODY), 0, 0);
        source_queues[8].push(f);
    }

    int max_cycles = 150;
    bool saw_vc1 = false;
    bool saw_vc0_after_dim_change = false;

    for (int cycle = 0; cycle < max_cycles; ++cycle) {
        // Injection Phase
        for (int i = 0; i < 9; ++i) {
            while (!source_queues[i].empty()) {
                Flit f = source_queues[i].front();
                if (routers[i]->inject_flit(f)) {
                    source_queues[i].pop();
                    total_injected++;
                } else {
                    break;
                }
            }
        }

        for (const auto& r : routers) r->evaluate(cycle);
        for (const auto& r : routers) r->update();

        // Check Credit Conservation
        for (const auto& r : routers) {
            for (int out_port = 1; out_port < r->num_ports; ++out_port) {
                Router* next_r = r->neighbors[out_port];
                int ingress_port = r->neighbor_ingress_ports[out_port];
                if (next_r) {
                    for (int v = 0; v < num_vcs; ++v) {
                        int current_credits = r->downstream_credits[out_port][v];
                        int receiving_buffer_occupancy = next_r->input_buffers[ingress_port][v].size();

                        EXPECT_GE(current_credits, 0) << "Credits went negative!";
                        EXPECT_EQ(current_credits + receiving_buffer_occupancy, buffer_size) << "Credit invariant violated!";
                    }
                }
            }
        }

        // Check Flit Conservation
        int buffered = get_total_buffered_flits();
        int ejected = get_total_ejected_flits();
        EXPECT_EQ(total_injected, buffered + ejected) << "Flit conservation violated at cycle " << cycle;

        // Track Dateline One-Directionality and VC resets
        for (const auto& r : routers) {
            for (int p = 0; p < r->num_ports; ++p) {
                for (int v = 0; v < num_vcs; ++v) {
                    std::queue<Flit> q = r->input_buffers[p][v];
                    while (!q.empty()) {
                        Flit f = q.front();
                        q.pop();

                        EXPECT_GE(f.vc_id, 0);
                        EXPECT_LE(f.vc_id, 1);
                        EXPECT_EQ(f.vc_id, v);

                        if (f.vc_id == 1) {
                            saw_vc1 = true;
                        }

                        // If it's at an intermediate node on the Y dimension (e.g., node 2 or 6) it should be on VC0
                        if (f.packet_id == 0 && r->id == 2 && p == 4) {
                            // Flit from 0 arrived at 2 via wrap (West). Should be VC1 here, but when it moves to Y (South), it should reset.
                        }
                        if (f.packet_id == 0 && r->id == 5 && p == 1) {
                            // Arrived at 5 from 2 via North ingress (so sent South from 2)
                            if (f.vc_id == 0) saw_vc0_after_dim_change = true;
                        }
                    }
                }
            }
        }
    }

    EXPECT_EQ(total_injected, 24);
    EXPECT_EQ(get_total_ejected_flits(), total_injected);
    EXPECT_TRUE(saw_vc1);
    EXPECT_TRUE(saw_vc0_after_dim_change);
}

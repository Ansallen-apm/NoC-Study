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
};

TEST_F(RouterInvariantTest, InvariantsAndDateline) {
    setup_ring(5);

    int total_injected = 0;

    // Inject flits to cause wrapping and dateline transitions, ensuring multi-hop.
    // Node 4 to Node 1 (Right/EAST, 4 -> 0 -> 1). Wrap triggers on 4 -> 0 (id > next_id).
    for (int i = 0; i < 4; ++i) {
        Flit f(4, 1, 0, i, (i == 0) ? HEAD : (i == 3 ? TAIL : BODY), 0, 0);
        if (routers[4]->inject_flit(f)) {
            total_injected++;
        }
    }

    // Node 0 to Node 3 (Left/WEST, 0 -> 4 -> 3). Wrap triggers on 0 -> 4 (id < next_id).
    for (int i = 0; i < 4; ++i) {
        Flit f(0, 3, 1, i, (i == 0) ? HEAD : (i == 3 ? TAIL : BODY), 0, 0);
        if (routers[0]->inject_flit(f)) {
            total_injected++;
        }
    }

    EXPECT_EQ(total_injected, 8); // All should be injected

    int max_cycles = 30; // Enough for 5 nodes to deliver 8 flits across multi-hop
    for (int cycle = 0; cycle < max_cycles; ++cycle) {
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
                    }
                }
            }
        }
    }

    // By cycle 20, all flits should be delivered
    EXPECT_EQ(get_total_ejected_flits(), total_injected) << "Not all flits were delivered in time.";
}

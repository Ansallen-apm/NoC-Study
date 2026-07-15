#include <gtest/gtest.h>
#include "../Routing.h"
#include "../Router.h"

// Dummy router just to provide an ID for the compute_next_hop methods
class DummyRouter : public Router {
public:
    DummyRouter(int id) : Router(id, 5, 2, 4, nullptr) {}
};

TEST(RoutingTest, XYRouting) {
    XYRouting algo(4, 4); // 4x4 Mesh
    DummyRouter r5(5);    // Located at (1, 1)

    // LOCAL
    EXPECT_EQ(algo.compute_next_hop(&r5, 5), 0);

    // EAST (dst at (2, 1) -> id 6)
    EXPECT_EQ(algo.compute_next_hop(&r5, 6), 2);
    // WEST (dst at (0, 1) -> id 4)
    EXPECT_EQ(algo.compute_next_hop(&r5, 4), 4);

    // SOUTH (dst at (1, 2) -> id 9)
    EXPECT_EQ(algo.compute_next_hop(&r5, 9), 3);
    // NORTH (dst at (1, 0) -> id 1)
    EXPECT_EQ(algo.compute_next_hop(&r5, 1), 1);

    // XY Routing must route X first. dst at (3, 3) -> id 15
    // X distance is 2 (EAST), Y distance is 2 (SOUTH). Should go EAST.
    EXPECT_EQ(algo.compute_next_hop(&r5, 15), 2);

    DummyRouter r7(7); // Located at (3, 1)
    // dst at (0, 3) -> id 12. X distance is -3 (WEST), Y distance is 2 (SOUTH). Should go WEST.
    EXPECT_EQ(algo.compute_next_hop(&r7, 12), 4);
}

TEST(RoutingTest, TorusRouting) {
    TorusRouting algo(4, 4); // 4x4 Torus
    DummyRouter r5(5);    // Located at (1, 1)

    // LOCAL
    EXPECT_EQ(algo.compute_next_hop(&r5, 5), 0);

    // X-Dimension:
    // dst at (2, 1) -> id 6. dist_right=1, dist_left=3. Should go EAST(2).
    EXPECT_EQ(algo.compute_next_hop(&r5, 6), 2);
    // dst at (0, 1) -> id 4. dist_right=3, dist_left=1. Should go WEST(4).
    EXPECT_EQ(algo.compute_next_hop(&r5, 4), 4);
    // dst at (3, 1) -> id 7. dist_right=2, dist_left=2. Should go EAST(2) (tiebreaker).
    EXPECT_EQ(algo.compute_next_hop(&r5, 7), 2);

    DummyRouter r0(0); // Located at (0, 0)
    // dst at (3, 0) -> id 3. dist_right=3, dist_left=1. Should go WEST(4) (Wraparound!).
    EXPECT_EQ(algo.compute_next_hop(&r0, 3), 4);

    DummyRouter r3(3); // Located at (3, 0)
    // dst at (0, 0) -> id 0. dist_right=1, dist_left=3. Should go EAST(2) (Wraparound!).
    EXPECT_EQ(algo.compute_next_hop(&r3, 0), 2);

    // Y-Dimension:
    // dst at (1, 2) -> id 9. dist_down=1, dist_up=3. Should go SOUTH(3).
    EXPECT_EQ(algo.compute_next_hop(&r5, 9), 3);
    // dst at (1, 0) -> id 1. dist_down=3, dist_up=1. Should go NORTH(1).
    EXPECT_EQ(algo.compute_next_hop(&r5, 1), 1);

    // dst at (1, 3) -> id 13. dist_down=2, dist_up=2. Should go SOUTH(3) (tiebreaker).
    EXPECT_EQ(algo.compute_next_hop(&r5, 13), 3);

    // dst at (0, 3) -> id 12 from r0(0,0). dist_down=3, dist_up=1. Should go NORTH(1) (Wraparound!).
    EXPECT_EQ(algo.compute_next_hop(&r0, 12), 1);

    DummyRouter r12(12); // Located at (0, 3)
    // dst at (0, 0) -> id 0 from r12(0,3). dist_down=1, dist_up=3. Should go SOUTH(3) (Wraparound!).
    EXPECT_EQ(algo.compute_next_hop(&r12, 0), 3);

    // Dimension Order Routing (X first):
    // dst at (3, 3) -> id 15 from r0(0,0). X differs, should go WEST(4) (Wraparound X).
    EXPECT_EQ(algo.compute_next_hop(&r0, 15), 4);
}

TEST(RoutingTest, RingRouting) {
    RingRouting algo(5); // 5-node Ring
    DummyRouter r0(0);
    DummyRouter r1(1);
    DummyRouter r2(2);

    // LOCAL
    EXPECT_EQ(algo.compute_next_hop(&r0, 0), 0);

    // Direct
    EXPECT_EQ(algo.compute_next_hop(&r0, 1), 1); // EAST
    EXPECT_EQ(algo.compute_next_hop(&r0, 2), 1); // EAST

    // Wraparound
    EXPECT_EQ(algo.compute_next_hop(&r0, 4), 2); // WEST (Wraparound: 0 -> 4 is shorter left)
    EXPECT_EQ(algo.compute_next_hop(&r0, 3), 2); // WEST (Wraparound: 0 -> 3 is shorter left)

    EXPECT_EQ(algo.compute_next_hop(&r1, 4), 2); // WEST (1 -> 0 -> 4 is shorter left)
    EXPECT_EQ(algo.compute_next_hop(&r2, 4), 1); // EAST (2 -> 3 -> 4 is shorter right, dist 2 vs 3)
}

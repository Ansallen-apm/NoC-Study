#ifndef TOPOLOGY_H
#define TOPOLOGY_H

#include <vector>

class Router; // Forward declaration

// Abstract base class for Network Topologies
class Topology {
public:
    virtual ~Topology() = default;

    // Returns the total number of nodes in this topology
    virtual int get_num_nodes() const = 0;

    // Returns the max number of ports per router needed (including local)
    virtual int get_max_ports() const = 0;

    // Connects all routers in the vector based on the topology rules
    virtual void build_network(std::vector<Router*>& routers) = 0;
};

class MeshTopology : public Topology {
private:
    int width, height;
public:
    MeshTopology(int w, int h) : width(w), height(h) {}
    int get_num_nodes() const override { return width * height; }
    int get_max_ports() const override { return 5; } // LOCAL, N, E, S, W
    void build_network(std::vector<Router*>& routers) override;
};

class RingTopology : public Topology {
private:
    int num_nodes;
public:
    RingTopology(int nodes) : num_nodes(nodes) {}
    int get_num_nodes() const override { return num_nodes; }
    int get_max_ports() const override { return 3; } // LOCAL, E, W
    void build_network(std::vector<Router*>& routers) override;
};

#endif

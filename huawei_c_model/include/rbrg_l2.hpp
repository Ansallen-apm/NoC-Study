#ifndef RBRG_L2_HPP
#define RBRG_L2_HPP

#include "component.hpp"
#include "ring.hpp"
#include "config.hpp"
#include "router.hpp"
#include "swap_sink.hpp"
#include <memory>
#include <deque>
#include <vector>

// Die-to-Die Link pipeline model
struct D2DPipelineStage {
    bool valid = false;
    Flit flit;
};

class RBRG_L2 : public Component, public SwapSink {
public:
    int local_ring_id;
    int local_station_id;
    int remote_ring_id;
    int remote_station_id;

    int d2d_latency_cycles;
    int queue_depth;
    int initial_credits;
    int current_credits;

    Ring* local_ring = nullptr;
    Ring* remote_ring = nullptr;
    std::shared_ptr<Router> router;

    // Queues on Local Die (Die 0)
    std::deque<Flit> reserved_tx_buffer;

    bool can_accept_swap() const override {
        return reserved_tx_buffer.size() < static_cast<size_t>(queue_depth);
    }

    void accept_swap(const Flit& f) override {
        reserved_tx_buffer.push_back(f);
    }
    std::deque<Flit> local_rx_queue; // From local ring

    // Queues on Remote Die (Die 1)
    std::deque<Flit> remote_rx_queue; // From D2D link, waiting to inject to remote ring

    // D2D Link Pipeline
    std::vector<D2DPipelineStage> d2d_pipeline_curr;
    std::vector<D2DPipelineStage> d2d_pipeline_next;

    // Credit Return Pipeline (simple bool array, latency = d2d_latency_cycles)
    std::vector<bool> credit_pipeline_curr;
    std::vector<bool> credit_pipeline_next;

    RBRG_L2(int l_ring, int l_station, int r_ring, int r_station,
            const BridgeConfig& config, int q_depth, int c_depth,
            std::shared_ptr<Router> router_ptr);

    void set_local_ring(Ring* r) { local_ring = r; }
    void set_remote_ring(Ring* r) { remote_ring = r; }

    void tick() override;
    void tock() override;

    size_t get_local_rx_queue_size() const { return local_rx_queue.size(); }
    size_t get_remote_rx_queue_size() const { return remote_rx_queue.size(); }
};

#endif // RBRG_L2_HPP

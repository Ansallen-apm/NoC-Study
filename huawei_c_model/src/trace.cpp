#include "trace.hpp"
#include "simulator.hpp"
#include <iostream>

void TraceDumper::dump_topology(Simulator* sim) {
    if (!active) return;

    // For 3x3 AI processor, we extract layout info roughly.
    // In our model, stations have IDs, but for the UI we need names like "V0_S1"

    // Nodes
    for (auto* r : sim->rings) {
        bool is_vertical = false; // We can infer from ID or just assume < 100 is vertical if we structure config well
        // For simplicity, let's prefix by ring ID.
        for (int s = 0; s < r->num_stations; ++s) {
            TraceTopologyNode n;
            n.name = "R" + std::to_string(r->ring_id) + "_S" + std::to_string(s);
            n.type = "station";
            top_nodes.push_back(n);

            // Ring Links
            TraceTopologyLink l;
            l.src = n.name;
            l.dst = "R" + std::to_string(r->ring_id) + "_S" + std::to_string((s + 1) % r->num_stations);
            l.type = "ring_cw";
            top_links.push_back(l);

            if (r->bidirectional) {
                TraceTopologyLink l2;
                l2.src = n.name;
                l2.dst = "R" + std::to_string(r->ring_id) + "_S" + std::to_string((s - 1 + r->num_stations) % r->num_stations);
                l2.type = "ring_ccw";
                top_links.push_back(l2);
            }
        }
    }

    // RBRG_L1 bridges
    for (auto& comp : sim->components) {
        if (auto* bridge = dynamic_cast<RBRG_L1*>(comp.get())) {
            TraceTopologyNode n;
            n.name = "BRG_" + std::to_string(bridge->local_ring_id) + "_" + std::to_string(bridge->remote_ring_id);
            n.type = "bridge";
            top_nodes.push_back(n);

            // Link from local station to bridge
            TraceTopologyLink l_in;
            l_in.src = "R" + std::to_string(bridge->local_ring_id) + "_S" + std::to_string(bridge->local_station_id);
            l_in.dst = n.name;
            l_in.type = "eject_to_bridge";
            top_links.push_back(l_in);

            // Link from bridge to remote station
            TraceTopologyLink l_out;
            l_out.src = n.name;
            l_out.dst = "R" + std::to_string(bridge->remote_ring_id) + "_S" + std::to_string(bridge->remote_station_id);
            l_out.type = "inject_to_ring";
            top_links.push_back(l_out);
        }
    }
}

void TraceDumper::capture_cycle(Simulator* sim, uint64_t cycle) {
    if (!active) return;
    TraceCycle tc;
    tc.cycle = cycle;

    // Capture Ring Slots (Links)
    for (auto* r : sim->rings) {
        for (int s = 0; s < r->num_stations; ++s) {
            TraceLink tl;
            tl.src_node = "R" + std::to_string(r->ring_id) + "_S" + std::to_string(s);
            tl.dst_node = "R" + std::to_string(r->ring_id) + "_S" + std::to_string((s + 1) % r->num_stations);
            if (r->curr_cw_slots[s].occupied) {
                tl.occupied = true;
                tl.flit_id = r->curr_cw_slots[s].flit.id;
            }
            tc.links.push_back(tl);

            if (r->bidirectional) {
                TraceLink tl2;
                tl2.src_node = "R" + std::to_string(r->ring_id) + "_S" + std::to_string(s);
                tl2.dst_node = "R" + std::to_string(r->ring_id) + "_S" + std::to_string((s - 1 + r->num_stations) % r->num_stations);
                if (r->curr_ccw_slots[s].occupied) {
                    tl2.occupied = true;
                    tl2.flit_id = r->curr_ccw_slots[s].flit.id;
                }
                tc.links.push_back(tl2);
            }
        }
    }

    // Capture Bridge Buffers
    for (auto& comp : sim->components) {
        if (auto* bridge = dynamic_cast<RBRG_L1*>(comp.get())) {
            std::string bname = "BRG_" + std::to_string(bridge->local_ring_id) + "_" + std::to_string(bridge->remote_ring_id);

            TraceBuffer t_ing;
            t_ing.node_name = bname;
            t_ing.buffer_name = "ingress";
            t_ing.current_size = bridge->ingress_queue.size();
            t_ing.capacity = bridge->queue_depth;
            for (const auto& f : bridge->ingress_queue) t_ing.flit_ids.push_back(f.id);
            tc.buffers.push_back(t_ing);

            TraceBuffer t_eg;
            t_eg.node_name = bname;
            t_eg.buffer_name = "egress";
            t_eg.current_size = bridge->egress_queue.size();
            t_eg.capacity = bridge->queue_depth;
            for (const auto& f : bridge->egress_queue) t_eg.flit_ids.push_back(f.id);
            tc.buffers.push_back(t_eg);
        }
    }

    // Station Eject/Inject Buffers (Optional, could be verbose)
    for (auto* st : sim->stations) {
        std::string sname = "R" + std::to_string(st->ring->ring_id) + "_S" + std::to_string(st->station_id);
        for (int k=0; k<2; ++k) {
            if (st->node_if[k].eject_q.size() > 0) {
                TraceBuffer tb;
                tb.node_name = sname;
                tb.buffer_name = "eject_" + std::to_string(k);
                tb.current_size = st->node_if[k].eject_q.size();
                tb.capacity = st->node_if[k].eject_q.capacity;
                for (const auto& f : st->node_if[k].eject_q.q) tb.flit_ids.push_back(f.id);
                tc.buffers.push_back(tb);
            }
            if (st->node_if[k].inject_q.size() > 0) {
                TraceBuffer tb;
                tb.node_name = sname;
                tb.buffer_name = "inject_" + std::to_string(k);
                tb.current_size = st->node_if[k].inject_q.size();
                tb.capacity = st->node_if[k].inject_q.capacity;
                for (const auto& f : st->node_if[k].inject_q.q) tb.flit_ids.push_back(f.id);
                tc.buffers.push_back(tb);
            }
        }
    }

    cycles.push_back(tc);
}

void TraceDumper::write_json() {
    if (!active) return;
    std::ofstream out(filepath);
    out << "{\n";

    // Topology
    out << "  \"topology\": {\n";
    out << "    \"nodes\": [\n";
    for (size_t i=0; i<top_nodes.size(); ++i) {
        out << "      { \"id\": \"" << top_nodes[i].name << "\", \"type\": \"" << top_nodes[i].type << "\" }";
        if (i < top_nodes.size()-1) out << ",";
        out << "\n";
    }
    out << "    ],\n";
    out << "    \"links\": [\n";
    for (size_t i=0; i<top_links.size(); ++i) {
        out << "      { \"src\": \"" << top_links[i].src << "\", \"dst\": \"" << top_links[i].dst << "\", \"type\": \"" << top_links[i].type << "\" }";
        if (i < top_links.size()-1) out << ",";
        out << "\n";
    }
    out << "    ]\n";
    out << "  },\n";

    // Cycles
    out << "  \"cycles\": [\n";
    for (size_t i=0; i<cycles.size(); ++i) {
        out << "    {\n";
        out << "      \"cycle\": " << cycles[i].cycle << ",\n";
        out << "      \"links\": [\n";
        for (size_t j=0; j<cycles[i].links.size(); ++j) {
            auto& l = cycles[i].links[j];
            out << "        { \"src\": \"" << l.src_node << "\", \"dst\": \"" << l.dst_node
                << "\", \"occupied\": " << (l.occupied ? "true" : "false")
                << ", \"flit_id\": " << l.flit_id << " }";
            if (j < cycles[i].links.size()-1) out << ",";
            out << "\n";
        }
        out << "      ],\n";
        out << "      \"buffers\": [\n";
        for (size_t j=0; j<cycles[i].buffers.size(); ++j) {
            auto& b = cycles[i].buffers[j];
            out << "        { \"node\": \"" << b.node_name << "\", \"type\": \"" << b.buffer_name
                << "\", \"size\": " << b.current_size << ", \"capacity\": " << b.capacity << ", \"flits\": [";
            for (size_t k=0; k<b.flit_ids.size(); ++k) {
                out << b.flit_ids[k];
                if (k < b.flit_ids.size()-1) out << ",";
            }
            out << "] }";
            if (j < cycles[i].buffers.size()-1) out << ",";
            out << "\n";
        }
        out << "      ]\n";
        out << "    }";
        if (i < cycles.size()-1) out << ",";
        out << "\n";
    }
    out << "  ]\n";
    out << "}\n";
    out.close();
}

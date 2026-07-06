#ifndef NODE_INTERFACE_HPP
#define NODE_INTERFACE_HPP

#include "flit.hpp"
#include <deque>
#include <cstddef>

class InjectQueue {
public:
    size_t capacity = 16;
    std::deque<Flit> q;

    bool can_push() const { return q.size() < capacity; }
    bool can_pop() const { return !q.empty(); }
    Flit& front() { return q.front(); }
    const Flit& front() const { return q.front(); }

    void push(const Flit& f) {
        if (can_push()) {
            q.push_back(f);
        }
    }

    void pop() {
        if (can_pop()) {
            q.pop_front();
        }
    }
};

#include <unordered_set>

class EjectQueue {
public:
    size_t capacity = 16;
    std::deque<Flit> q;
    std::unordered_set<uint64_t> reserved_flit_ids;

    // Checks if there is space for a NORMAL (unreserved) flit
    // Normal space is capacity minus current actual occupany AND outstanding reservations
    bool has_space() const {
        return (q.size() + reserved_flit_ids.size()) < capacity;
    }

    // Checks if the EjectQueue has capacity to grant a NEW reservation
    // A reservation can be granted as long as the total number of reservations
    // doesn't exceed the queue's MAX capacity. We can reserve even if the queue
    // is currently full of actual flits!
    bool can_reserve() const {
        return reserved_flit_ids.size() < capacity;
    }

    void reserve(uint64_t flit_id) {
        if (can_reserve()) {
            reserved_flit_ids.insert(flit_id);
        }
    }

    bool is_reserved_for(uint64_t flit_id) const {
        return reserved_flit_ids.find(flit_id) != reserved_flit_ids.end();
    }

    void push(const Flit& f) {
        // If this flit had a reservation, consume it
        if (is_reserved_for(f.id)) {
            reserved_flit_ids.erase(f.id);
            q.push_back(f);
        } else if (has_space()) {
            // Normal unreserved injection
            q.push_back(f);
        }
    }
};

class NodeInterface {
public:
    InjectQueue inject_q;
    EjectQueue eject_q;
};

#endif // NODE_INTERFACE_HPP

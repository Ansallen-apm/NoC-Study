#ifndef NODE_INTERFACE_HPP
#define NODE_INTERFACE_HPP

#include "flit.hpp"
#include <deque>
#include <cstddef>

class InjectQueue {
public:
    size_t capacity = 16;
    std::deque<Flit> q;

    size_t size() const { return q.size(); }
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
    size_t max_reservations = 1;
    std::deque<Flit> q;
    std::unordered_set<uint64_t> reserved_flit_ids;

    // Checks if there is space for a NORMAL (unreserved) flit
    // Normal space is capacity minus current actual occupany AND outstanding reservations
    size_t size() const { return q.size(); }
    bool is_full() const {
        return q.size() >= capacity;
    }

    Flit pop_oldest() {
        if (q.empty()) return Flit();
        Flit f = q.front();
        q.pop_front();
        return f;
    }

    bool has_space() const {
        // Normal injection requires actual space (not exceeding capacity with reserves)
        // A normal flit can only enter if doing so wouldn't steal a reserved spot.
        // So we need: current size + number of reservations < total capacity
        return (q.size() + reserved_flit_ids.size()) < capacity;
    }

    bool can_reserve() const {
        // A flit can reserve a spot as long as we haven't hit the reservation limit.
        return reserved_flit_ids.size() < max_reservations;
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

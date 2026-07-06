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

class EjectQueue {
public:
    size_t capacity = 16;
    std::deque<Flit> q;

    bool has_space() const { return q.size() < capacity; }

    void push(const Flit& f) {
        if (has_space()) {
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

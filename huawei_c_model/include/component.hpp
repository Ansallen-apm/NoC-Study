#ifndef COMPONENT_HPP
#define COMPONENT_HPP

class Component {
public:
    virtual void tick() = 0;   // 計算本 cycle 的 next-state decision
    virtual void tock() = 0;   // 在 clock edge commit state
    virtual ~Component() = default;
};

#endif // COMPONENT_HPP

# NoC Architecture

## 1. Top Level Architecture
*   **Topology**: 2D Mesh (Configurable Dimensions, default 4x4).
*   **Routing**: XY Routing (Deterministic).
    *   Route X first, then Y.
*   **Flow Control**: Store-and-Forward (for simplicity in first version) or Credit-Based.
    *   *Decision*: We will implement a simplified **packet-switched** mechanism with buffer availability checks.
*   **Switching**: Packet Switching.

## 2. Micro-Architecture (Router)
*   **Ports**: 5 Ports (Local, North, East, South, West).
*   **Input Buffers**: FIFO queue at each input port.
*   **Arbiter**: Round-Robin Arbitration for switch traversal.
*   **Crossbar**: Fully connected (or implicitly handled by muxes).

## 3. Bus & Signals
*   **Data Width**: 32-bit payload.
*   **Control Signals**: Valid, Ready (Handshake).

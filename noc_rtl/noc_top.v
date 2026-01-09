module noc_top (
    input clk,
    input reset
);
    // 2x2 Mesh Instantiation

    // Wires connecting routers...

    // Router 0
    router r0 (
        .clk(clk),
        .reset(reset),
        .router_id(4'd0),
        // ... connections
        .in_data_0(32'b0), .in_valid_0(1'b0) // Tie unused inputs
    );

    // Router 1
    router r1 (
        .clk(clk),
        .reset(reset),
        .router_id(4'd1),
        // ... connections
        .in_data_0(32'b0), .in_valid_0(1'b0)
    );

    // ...

endmodule

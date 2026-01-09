module noc_top (
    input clk,
    input reset
);
    // 2x2 Mesh Instantiation (2x2 網格實例化)

    // Wires connecting routers... (連接路由器的線路...)

    // Router 0 (路由器 0)
    router r0 (
        .clk(clk),
        .reset(reset),
        .router_id(4'd0),
        // ... connections (連接)
        .in_data_0(32'b0), .in_valid_0(1'b0) // Tie unused inputs (綁定未使用的輸入)
    );

    // Router 1 (路由器 1)
    router r1 (
        .clk(clk),
        .reset(reset),
        .router_id(4'd1),
        // ... connections (連接)
        .in_data_0(32'b0), .in_valid_0(1'b0)
    );

    // ...

endmodule

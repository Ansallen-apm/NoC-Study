module router (
    input clk,
    input reset,

    // 5 Input Ports (Data + Valid)
    input [31:0] in_data_0, input in_valid_0, output reg out_ready_0,
    input [31:0] in_data_1, input in_valid_1, output reg out_ready_1,
    input [31:0] in_data_2, input in_valid_2, output reg out_ready_2,
    input [31:0] in_data_3, input in_valid_3, output reg out_ready_3,
    input [31:0] in_data_4, input in_valid_4, output reg out_ready_4,

    // 5 Output Ports (Data + Valid)
    output reg [31:0] out_data_0, output reg out_valid_0, input in_ready_0,
    output reg [31:0] out_data_1, output reg out_valid_1, input in_ready_1,
    output reg [31:0] out_data_2, output reg out_valid_2, input in_ready_2,
    output reg [31:0] out_data_3, output reg out_valid_3, input in_ready_3,
    output reg [31:0] out_data_4, output reg out_valid_4, input in_ready_4,

    input [3:0] router_id // ID for routing
);

    parameter MESH_WIDTH = 4;

    wire [3:0] my_x = router_id % MESH_WIDTH;
    wire [3:0] my_y = router_id / MESH_WIDTH;

    // Simplified Logic:
    // We need to route based on header. Assuming data contains destination.
    // For this skeleton, let's assume bits [31:16] are data, [15:8] are dst_id.

    // In a real implementation, we would buffer inputs.
    // Here we implement a very basic combinatorial routing decision for Port 0 (Local Input) for demonstration.

    always @(*) begin
        // Default ready
        out_ready_0 = 1'b1; // Ready to receive

        // Default output
        out_valid_2 = 1'b0; // East
        out_data_2 = 32'b0;

        // Simple example: Route local input (0) to East (2) if dst_x > my_x
        if (in_valid_0) begin
            // Extract dst logic
            // integer dst_id = in_data_0[15:8]; // Placeholder
            // integer dst_x = dst_id % MESH_WIDTH;

            // For skeleton, just pass through to East
            out_valid_2 = in_valid_0;
            out_data_2 = in_data_0;
        end
    end

    // Instantiate Arbiter (skeleton kept)
    wire [4:0] requests;
    wire [4:0] grants;

    assign requests = {in_valid_4, in_valid_3, in_valid_2, in_valid_1, in_valid_0};

    arbiter arb_inst (
        .clk(clk),
        .reset(reset),
        .req(requests),
        .grant(grants)
    );

endmodule

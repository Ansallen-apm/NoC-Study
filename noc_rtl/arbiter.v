module arbiter (
    input clk,
    input reset,
    input [4:0] req,    // Requests from 5 ports
    output reg [4:0] grant // Grant to 5 ports (One-hot)
);
    // Simple Round Robin Arbiter
    reg [2:0] last_grant;

    always @(posedge clk or posedge reset) begin
        if (reset) begin
            grant <= 5'b00000;
            last_grant <= 0;
        end else begin
            // Simplified priority logic
            // In a real RR, we rotate based on last_grant
            // This is a fixed priority for demo
            if (req[0]) grant <= 5'b00001;
            else if (req[1]) grant <= 5'b00010;
            else if (req[2]) grant <= 5'b00100;
            else if (req[3]) grant <= 5'b01000;
            else if (req[4]) grant <= 5'b10000;
            else grant <= 5'b00000;
        end
    end
endmodule

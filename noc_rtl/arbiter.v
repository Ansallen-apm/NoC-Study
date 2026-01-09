module arbiter (
    input clk,
    input reset,
    input [4:0] req,    // Requests from 5 ports (來自 5 個埠的請求)
    output reg [4:0] grant // Grant to 5 ports (One-hot) (授權給 5 個埠，獨熱編碼)
);
    // Simple Round Robin Arbiter (簡單輪詢仲裁器)
    reg [2:0] last_grant;

    always @(posedge clk or posedge reset) begin
        if (reset) begin
            grant <= 5'b00000;
            last_grant <= 0;
        end else begin
            // Simplified priority logic (簡化的優先級邏輯)
            // In a real RR, we rotate based on last_grant (在真實輪詢中，我們根據 last_grant 輪轉)
            // This is a fixed priority for demo (這是用於展示的固定優先級)
            if (req[0]) grant <= 5'b00001;
            else if (req[1]) grant <= 5'b00010;
            else if (req[2]) grant <= 5'b00100;
            else if (req[3]) grant <= 5'b01000;
            else if (req[4]) grant <= 5'b10000;
            else grant <= 5'b00000;
        end
    end
endmodule

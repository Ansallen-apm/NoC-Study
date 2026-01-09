# Trace Format Specification (Trace 格式規範)

The trace file is a plain text file where each line represents a packet injection event.
(Trace 檔案是一個純文字檔，每一行代表一個封包注入事件。)

## Format (格式)
```
<src_id> <dst_id> <payload_data>
```
*   `src_id`: Integer ID of the source node. For a WxH mesh, ID = y * W + x. (來源節點的整數 ID。對於 WxH 的網格，ID = y * W + x。)
*   `dst_id`: Integer ID of the destination node. (目的節點的整數 ID。)
*   `payload_data`: Integer representing the data payload (for verification). (代表資料負載的整數，用於驗證。)

## Example (4x4 Mesh) (範例：4x4 網格)
Node 0 is (0,0), Node 1 is (1,0)... Node 4 is (0,1).
(節點 0 是 (0,0)，節點 1 是 (1,0)... 節點 4 是 (0,1)。)

```
0 5 1001   # Node 0 sends to Node 5, data 1001 (節點 0 傳送至節點 5，資料 1001)
1 6 2002   # Node 1 sends to Node 6, data 2002 (節點 1 傳送至節點 6，資料 2002)
15 0 9999  # Node 15 sends to Node 0, data 9999 (節點 15 傳送至節點 0，資料 9999)
```

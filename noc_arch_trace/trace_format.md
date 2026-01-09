# Trace Format Specification

The trace file is a plain text file where each line represents a packet injection event.

## Format
```
<src_id> <dst_id> <payload_data>
```
*   `src_id`: Integer ID of the source node. For a WxH mesh, ID = y * W + x.
*   `dst_id`: Integer ID of the destination node.
*   `payload_data`: Integer representing the data payload (for verification).

## Example (4x4 Mesh)
Node 0 is (0,0), Node 1 is (1,0)... Node 4 is (0,1).

```
0 5 1001   # Node 0 sends to Node 5, data 1001
1 6 2002   # Node 1 sends to Node 6, data 2002
15 0 9999  # Node 15 sends to Node 0, data 9999
```

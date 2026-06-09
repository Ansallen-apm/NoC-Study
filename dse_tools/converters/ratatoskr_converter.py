import yaml
import xml.etree.ElementTree as ET
import os

class RatatoskrConverter:
    def __init__(self, config_path):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

    def generate_config(self, output_config_path="config_ratatoskr.xml", output_network_path="network_ratatoskr.xml", report_name="report"):
        self.generate_network_xml(output_network_path)
        self.generate_sim_xml(output_network_path, output_config_path, report_name)

    def generate_network_xml(self, output_network_path):
        root = ET.Element("network-on-chip")

        arch_config = self.config.get("architecture", {})
        topo_type = arch_config.get("topology", "mesh")
        width = arch_config.get("width", 4)
        height = arch_config.get("height", 4)
        vcs = arch_config.get("num_vcs", 4)
        buf_size = arch_config.get("buffer_size", 8)
        routing = arch_config.get("routing", "xy").upper()
        if routing == "XY": routing = "XYZ" # Ratatoskr XYZ routing

        ET.SubElement(root, "bufferDepthType").set("value", "single")

        dims = ET.SubElement(root, "dimensions")
        ET.SubElement(dims, "x").set("value", str(width))
        ET.SubElement(dims, "y").set("value", str(height))
        ET.SubElement(dims, "z").set("value", "1")

        layers = ET.SubElement(root, "layers")
        ET.SubElement(layers, "layer").set("value", "0")

        ntypes = ET.SubElement(root, "nodeTypes")
        rt = ET.SubElement(ntypes, "nodeType", {"id": "0"})
        ET.SubElement(rt, "model").set("value", "RouterVC")
        ET.SubElement(rt, "routing").set("value", routing)
        ET.SubElement(rt, "selection").set("value", "1stFreeVC")
        ET.SubElement(rt, "clockDelay").set("value", "1")
        ET.SubElement(rt, "arbiterType").set("value", "fair")

        pe = ET.SubElement(ntypes, "nodeType", {"id": "1"})
        ET.SubElement(pe, "model").set("value", "ProcessingElement")
        ET.SubElement(pe, "clockDelay").set("value", "1")

        idtypes = ET.SubElement(root, "idTypes")
        num_routers = width * height
        for i in range(num_routers):
            idt = ET.SubElement(idtypes, "idType", {"id": str(i)})
            ET.SubElement(idt, "nodeType").set("value", "0")
        for i in range(num_routers):
            idt = ET.SubElement(idtypes, "idType", {"id": str(num_routers + i)})
            ET.SubElement(idt, "nodeType").set("value", "1")

        nodes = ET.SubElement(root, "nodes")
        for r_id in range(num_routers):
            n = ET.SubElement(nodes, "node", {"id": str(r_id)})
            x = r_id % width
            y = r_id // width
            ET.SubElement(n, "xPos").set("value", str(float(x) / width))
            ET.SubElement(n, "yPos").set("value", str(float(y) / height))
            ET.SubElement(n, "zPos").set("value", "0.0")
            ET.SubElement(n, "nodeType").set("value", "0")
            ET.SubElement(n, "idType").set("value", str(r_id))
            ET.SubElement(n, "layer").set("value", "0")

        for pe_id in range(num_routers):
            real_id = num_routers + pe_id
            n = ET.SubElement(nodes, "node", {"id": str(real_id)})
            x = pe_id % width
            y = pe_id // width
            ET.SubElement(n, "xPos").set("value", str(float(x) / width))
            ET.SubElement(n, "yPos").set("value", str(float(y) / height))
            ET.SubElement(n, "zPos").set("value", "0.0")
            ET.SubElement(n, "nodeType").set("value", "1")
            ET.SubElement(n, "idType").set("value", str(real_id))
            ET.SubElement(n, "layer").set("value", "0")

        cons = ET.SubElement(root, "connections")
        con_id = 0
        bd_str = ", ".join([str(buf_size)] * vcs)

        for i in range(num_routers):
            con = ET.SubElement(cons, "con", {"id": str(con_id)})
            con_id += 1
            ports = ET.SubElement(con, "ports")
            p0 = ET.SubElement(ports, "port", {"id": "0"})
            ET.SubElement(p0, "node").set("value", str(i))
            ET.SubElement(p0, "bufferDepth").set("value", str(buf_size))
            ET.SubElement(p0, "buffersDepths").set("value", bd_str)
            ET.SubElement(p0, "vcCount").set("value", str(vcs))

            p1 = ET.SubElement(ports, "port", {"id": "1"})
            ET.SubElement(p1, "node").set("value", str(num_routers + i))
            ET.SubElement(p1, "bufferDepth").set("value", str(buf_size))
            ET.SubElement(p1, "buffersDepths").set("value", bd_str)
            ET.SubElement(p1, "vcCount").set("value", str(vcs))

        for i in range(num_routers):
            x = i % width
            y = i // width

            if x < width - 1:
                con = ET.SubElement(cons, "con", {"id": str(con_id)})
                con_id += 1
                ports = ET.SubElement(con, "ports")
                p0 = ET.SubElement(ports, "port", {"id": "0"})
                ET.SubElement(p0, "node").set("value", str(i))
                ET.SubElement(p0, "bufferDepth").set("value", str(buf_size))
                ET.SubElement(p0, "buffersDepths").set("value", bd_str)
                ET.SubElement(p0, "vcCount").set("value", str(vcs))

                p1 = ET.SubElement(ports, "port", {"id": "1"})
                ET.SubElement(p1, "node").set("value", str(i + 1))
                ET.SubElement(p1, "bufferDepth").set("value", str(buf_size))
                ET.SubElement(p1, "buffersDepths").set("value", bd_str)
                ET.SubElement(p1, "vcCount").set("value", str(vcs))

            if y < height - 1:
                con = ET.SubElement(cons, "con", {"id": str(con_id)})
                con_id += 1
                ports = ET.SubElement(con, "ports")
                p0 = ET.SubElement(ports, "port", {"id": "0"})
                ET.SubElement(p0, "node").set("value", str(i))
                ET.SubElement(p0, "bufferDepth").set("value", str(buf_size))
                ET.SubElement(p0, "buffersDepths").set("value", bd_str)
                ET.SubElement(p0, "vcCount").set("value", str(vcs))

                p1 = ET.SubElement(ports, "port", {"id": "1"})
                ET.SubElement(p1, "node").set("value", str(i + width))
                ET.SubElement(p1, "bufferDepth").set("value", str(buf_size))
                ET.SubElement(p1, "buffersDepths").set("value", bd_str)
                ET.SubElement(p1, "vcCount").set("value", str(vcs))

        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ", level=0)
        tree.write(output_network_path, encoding="utf-8", xml_declaration=True)

    def generate_sim_xml(self, net_path, out_path, report_name):
        root = ET.Element("configuration", {"xmlns:xsi":"http://www.w3.org/2001/XMLSchema-instance"})

        sim_config = self.config.get("simulation", {})
        arch_config = self.config.get("architecture", {})

        gen = ET.SubElement(root, "general")
        sim_cycles = sim_config.get("sim_cycles", 15000)
        ET.SubElement(gen, "simulationTime").set("value", str(sim_cycles))
        ET.SubElement(gen, "outputToFile", {"value":"true"}).text = report_name

        noc = ET.SubElement(root, "noc")
        ET.SubElement(noc, "nocFile").text = net_path
        ET.SubElement(noc, "flitsPerPacket").set("value", str(arch_config.get("packet_size", 1)))

        app = ET.SubElement(root, "application")
        ET.SubElement(app, "benchmark").text = "synthetic"
        syn = ET.SubElement(app, "synthetic")

        warm = ET.SubElement(syn, "phase", {"name":"warmup"})
        t_pattern = sim_config.get("traffic_pattern", "uniform")
        ET.SubElement(warm, "distribution").set("value", t_pattern)
        ET.SubElement(warm, "start", {"max":"100", "min":"100"})
        ET.SubElement(warm, "duration", {"max":"900", "min":"900"})
        ET.SubElement(warm, "repeat", {"max":"-1", "min":"-1"})
        ET.SubElement(warm, "delay", {"max":"0", "min":"0"})
        inj_rate = sim_config.get("injection_rate", 0.1)
        ET.SubElement(warm, "injectionRate").set("value", str(inj_rate))
        ET.SubElement(warm, "count", {"max":"1", "min":"1"})

        run = ET.SubElement(syn, "phase", {"name":"run"})
        ET.SubElement(run, "distribution").set("value", t_pattern)
        ET.SubElement(run, "start", {"max":"1000", "min":"1000"})
        ET.SubElement(run, "duration", {"max":str(sim_cycles), "min":str(sim_cycles)})
        ET.SubElement(run, "repeat", {"max":"-1", "min":"-1"})
        ET.SubElement(run, "delay", {"max":"0", "min":"0"})
        ET.SubElement(run, "injectionRate").set("value", str(inj_rate))
        ET.SubElement(run, "count", {"max":"1", "min":"1"})

        verb = ET.SubElement(root, "verbose")
        pe_v = ET.SubElement(verb, "processingElements")
        ET.SubElement(pe_v, "receive_tail_flit").set("value", "false")

        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ", level=0)
        tree.write(out_path, encoding="utf-8", xml_declaration=True)

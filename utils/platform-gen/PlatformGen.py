import argparse
from collections import OrderedDict
from typing import Dict
from itertools import cycle
import xml.dom.minidom as xml_format
import xml.etree.ElementTree as xml
import json

class FatTree:# {{{
    def __init__(self, levels: int, down: list[int], up: list[int], link_count: list[int], debug=False):
        self.debug = debug
        self.levels = levels

        assert len(down) == levels, "down len doesnt match levels of the tree."
        self.down = down

        assert len(up) == levels, "up len doesnt match levels of the tree."
        self.up = up

        assert len(link_count) == levels, "link_count len doesnt match levels of the tree."
        self.link_count = link_count

        self.nodes  = {}
        self.routes = [] 


    def generate_compute_nodes(self):
        tot_elements = 1
        for i in self.down:
            tot_elements *= i

        self.nodes[0] = [ { 'id': f"c{i}", "type": "host" } for i in range(tot_elements) ]
        if self.debug: print(f"Creating {tot_elements} nodes")
        
    def generate_switches(self):
        k = 2 * sum(self.nodes_by_level)
        for i in range(self.levels):
            self.nodes[i + 1] = list() 
            for j in range(self.nodes_by_level[i+1]):
                curr = { 'id': f'r{i+1}{j}', 'type': 'router', 'up': (0, 0), 'dn': (0, 0) }
                k -= 1

                curr['dn'] = (self.down[i], self.link_count[i])
                if i != self.levels - 1:
                    curr['up'] = (self.up[i + 1], self.link_count[i + 1])

                self.nodes[i+1].append(curr)
                if self.debug: print(f"Creating router {curr['id']}")

    def generate_routes(self):
        for n in range(1, self.levels+1):
            prev_cycle = cycle(self.nodes[n-1])
            for i in self.nodes[n]:
                for j in [ next(prev_cycle) for _ in range(i['dn'][0]) ]:
                    self.routes.append({ 'src': i['id'], 'dst': j['id'] }) 
                    if self.debug: print(f"Creating route ({i['id']}, {j['id']})")


    def generate(self):
        self.generate_compute_nodes()

        self.nodes_by_level = [0 for _ in range(self.levels + 1) ]
        self.nodes_by_level[0] = 1

        for i in range(self.levels):
            self.nodes_by_level[0] *= self.down[i]

        for i in range(self.levels):
            thisLevel = 1

            for j in range(i+1):
                thisLevel *= self.up[j]

            for j in range(i+1, self.levels):
                thisLevel *= self.down[j]

            self.nodes_by_level[i+1] = thisLevel

        if self.debug: print("Nodes by level", self.nodes_by_level)
            
        self.generate_switches()
        self.generate_routes()

class FileInterface:
    def __init__(self, input_json: str, output_xml: str):
        with open(input_json, "r") as platform_file:
            self.platform = json.load(platform_file)

        self.output = output_xml
        self.files = {}
        # Node file
        with open("node_types.json", "r") as nodes_file:
            self.files["nodes"] = json.load(nodes_file)

        assert sum([ int(i["type"] not in self.files["nodes"].keys()) for i in self.platform["nodes"] ]) == 0, "Node type not found in node type file"  

    def gen_subelement(self, zone, element_type: str, attrs: Dict[str, str], props: list[Dict[str, str]] = []):
        sub_element = xml.SubElement(zone, element_type, attrib=OrderedDict(attrs) )
        for i in props:
            xml.SubElement(sub_element, "prop", attrib=OrderedDict({ "id": i["id"], "value": i["value"] }))

        return sub_element


    def write(self, fat_tree: FatTree):
        assert sum([ int(i["number"]) for i in self.platform["nodes"] ]) == fat_tree.nodes_by_level[0], "Number of nodes of the fat tree does not match the number specified in the platform file"

        platform_xml = xml.Element("platform", attrib=OrderedDict({"version": "4.1"}))
        main_zone = self.gen_subelement(platform_xml, "zone", {"id": "main", "routing": "Full"})

        cluster_compute = self.gen_subelement(main_zone, "zone", {"id": "cluster_compute", "routing": "Full"})
        # Compute nodes
        for i in self.platform["nodes"]:
            nodes_iter = iter(fat_tree.nodes[0])
            for j in range(int(i["number"])):
                curr = next(nodes_iter)
                node_type = self.files["nodes"][i["type"]]
                node_type["attributes"]["id"] = curr["id"]

                self.gen_subelement(cluster_compute, curr["type"], node_type["attributes"])

        # Routers
        for n in range(1, fat_tree.levels+1):
            for i in fat_tree.nodes[n]:
                self.gen_subelement(cluster_compute, "router", {"id": i["id"]})
        self.gen_subelement(cluster_compute, "router", {"id": "router_master"})

        for i in fat_tree.routes:
            self.gen_subelement(cluster_compute, "link", {"id": f"{i['src']}-{i['dst']}", "bandwidth": "125MBps", "latency": "100us" })

        for i in fat_tree.nodes[max(fat_tree.nodes.keys())]:
            self.gen_subelement(cluster_compute, "link", {"id": f"router_master-{i['id']}", "bandwidth": "125MBps", "latency": "100us" })

        for i in fat_tree.routes:
            route = self.gen_subelement(cluster_compute, "route", {"src": i['src'], "dst": i['dst']})
            self.gen_subelement(route, "link_ctn", {"id": f"{i['src']}-{i['dst']}"})

        for i in fat_tree.nodes[max(fat_tree.nodes.keys())]:
            route = self.gen_subelement(cluster_compute, "route", {"src": "router_master", "dst": i['id']})
            self.gen_subelement(route, "link_ctn", {"id": f"router_master-{i['id']}"})

        # MASTER ZONE
        self.gen_subelement(main_zone, "cluster", {
            "id": "cluster_master", "prefix": "master_host", "suffix": "", "radical": "0-0", "speed": "100.0Mf",
            "bw": "125MBps", "lat": "50us", "bb_bw": "2.25GBps", "bb_lat": "500us"
            }, [ { "id": "role", "value": "master" } ])

        # CLUSTERS LINK
        self.gen_subelement(main_zone, "link", { "id": "backbone", "bandwidth": "1.25GBps", "latency": "500us" })
        zoneRoute = self.gen_subelement(main_zone, "zoneRoute", { "src": "cluster_compute", "dst": "cluster_master", "gw_src": "router_master", "gw_dst": "master_hostcluster_master_router" })
        self.gen_subelement(zoneRoute, "link_ctn", {"id": f"backbone"})

        def doctype():
            return "<!DOCTYPE platform SYSTEM \"https://simgrid.org/simgrid.dtd\">"

        with open(self.output, "w") as out:
            out.write(xml_format.parseString("{}{}".format(doctype(),
                        xml.tostring(platform_xml).decode())).toprettyxml(indent="    ",
                            encoding="utf-8").decode())

'''
A = FatTree(2, [4, 4], [1, 2], [2, 2], debug=False)
A.generate()
print("--")

B = FileInterface("test02.json", "generated.xml")
B.write(A)
'''

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="A")
    ap.add_argument("-p", "--platform-file", type=str, required=True, help="JSON with platform description")
    ap.add_argument("-f", "--fat-tree", type=str, required=True, help="Structure of the fat tree")
    ap.add_argument("-o", "--output-xml", type=str, default="platform.xml", help="XML output with platform ready for Batsim")

    args = ap.parse_args()

    levels, dn, up, lk = args.fat_tree.split(";")
    levels = int(levels)
    dn = [ int(i) for i in dn.split(",") ]
    up = [ int(i) for i in up.split(",") ]
    lk = [ int(i) for i in lk.split(",") ]

    assert len(up) == len(dn) == len(lk) == levels

    tree = FatTree(levels, dn, up, lk, debug=True) 
    iface = FileInterface(args.platform_file, args.output_xml)

    tree.generate()
    iface.write(tree)

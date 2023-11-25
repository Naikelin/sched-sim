import argparse
from collections import OrderedDict
from typing import Dict, Tuple
from itertools import cycle
import xml.dom.minidom as xml_format
import xml.etree.ElementTree as xml
import json
import networkx as nx
import matplotlib.pyplot as plt
import random
from networkx.drawing.nx_pydot import graphviz_layout


class Node:
    def __init__(self, id: str, node_type: str, up: Tuple[int, int] = (0, 0), dn: Tuple[int, int] = (0, 0)):
        self.id   = id
        self.type = node_type
        self.up   = up
        self.dn   = dn

        self.parents = []
        self.children = []

class FatTree:
    def __init__(self, levels: int, down: list[int], up: list[int], link_count: list[int], debug=False):
        self.debug = debug
        self.levels = levels

        assert len(down) == levels, "down len doesnt match levels of the tree."
        self.down = down

        assert len(up) == levels, "up len doesnt match levels of the tree."
        self.up = up

        assert sum([ int(i > j) for i, j in zip(up, down) ]) == 0, "There can't exist more uplinks that nodes in the upper level."

        assert len(link_count) == levels, "link_count len doesnt match levels of the tree."
        self.link_count = link_count

        self.nodes  = {}
        #self.routes = { 'up': [], 'dn': [] }
        self.routes = {}

    def _generate_compute_nodes(self):
        """
            Calculates the number of compute nodes and instanciates them.
        """
        tot_elements = 1
        for i in self.down:
            tot_elements *= i

        empty_node = lambda i: Node(f"c{i}", "host", (self.up[0], self.link_count[0]))
        self.nodes[0] = [ empty_node(i) for i in range(tot_elements) ]

        if self.debug: print(f"[+] Creating {tot_elements} nodes")

    def _generate_switches(self):
        """
            Instanciates routers of each level.
        """
        k = 2 * sum(self.nodes_by_level)

        for i in range(self.levels):
            self.nodes[i + 1] = list()
            for j in range(self.nodes_by_level[i+1]):
                curr = Node(f"r{i+1}{j}", "router", (0,0), (0,0) )
                k -= 1

                curr.dn = (self.down[i], self.link_count[i])
                if i != self.levels - 1:
                    curr.up = (self.up[i + 1], self.link_count[i + 1])

                self.nodes[i+1].append(curr)
                if self.debug: print(f"[+] Creating router {curr.id}")

    def _generate_routes(self):
        """
            Iterates throwgh each Node and generates the corresponding links and routes.
        """
        for n in range(1,self.levels+1):
            prev_cycle = cycle(self.nodes[n-1])

            for i in self.nodes[n]:
                for j in [ next(prev_cycle) for _ in range(i.dn[0]) ]:
                    i.children.append(j.id)
                    j.parents.append(i.id)

        for i in sum(self.nodes.values(), []):
            for j in i.parents:
                self.routes[f'{j}-{i.id}'] = {'src': j, 'dst': i.id, 'up': i.up[1], 'dn': 0}

            for j in i.children:
                id = f'{i.id}-{j}'
                if id in self.routes:
                    self.routes[id]["dn"] = i.dn[1]
                else:
                    self.routes[id] = {'src': i.id, 'dst': j, 'up': 0, 'dn': 0}

        if self.debug:
            for i in self.routes.items():
                print(i)

    def generate(self):
        self._generate_compute_nodes()

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

        if self.debug: print("[+] Routers by level", self.nodes_by_level[1:])

        self._generate_switches()
        self._generate_routes()

    def draw(self):
        G = nx.DiGraph()

        edges = [ (i["src"], i["dst"]) for i in self.routes.values() ]
        G.add_edges_from(edges)

        options = {
            'node_color': 'black',
            'node_size': 100,
            'width': 3,
        }

        pos = graphviz_layout(G, prog="dot")
        nx.draw(G, pos, **options)

class FileInterface:
    def __init__(self, input_json: str, output_xml: str):
        with open(input_json, "r") as platform_file:
            self.platform = json.load(platform_file)

        self.output = output_xml
        self.files = {}
        # Node file
        with open("node_types.json", "r") as nodes_file:
            self.files["nodes"] = json.load(nodes_file)

        # Network file
        #with open("networks_types.json", "r") as networks_file:
        #    self.files["networks"] = json.load(networks_file)

        assert sum([ int(i["type"] not in self.files["nodes"].keys()) for i in self.platform["nodes"] ]) == 0, "Node type not found in node type file"

    def _generate_subelement(self, zone, element_type: str, attrs: Dict[str, str], props: list[Dict[str, str]] = []):
        sub_element = xml.SubElement(zone, element_type, attrib=OrderedDict(attrs) )
        for i in props:
            xml.SubElement(sub_element, "prop", attrib=OrderedDict({ "id": i["id"], "value": i["value"] }))

        return sub_element

    def _generate_compute_node(self, zone, attrs: Dict[str,str], props: list[ Dict[str,str] ] = []):
        prefixes = { 'G': 10e9, 'M': 10e6, "k": 10e3 }
        rev_prefixes = { j: i for i, j in prefixes.items() }

        def rm_prefix(x: str):
            return float(x[:-1]) * prefixes[x[-1]] if x[-1] in prefixes.keys() else float(x)

        '''
        def add_prefix(x: float):
            for i in rev_prefixes:
                if x // i != 0:
                    return f"{x//i}{rev_prefixes[i]}"
            return f"{x}"
        '''

        # Mod speed
        if "std" in attrs.keys():
            std = rm_prefix( attrs.pop("std")[:-1] )

            speeds = [ rm_prefix(i[:-1]) for i in attrs["speed"].replace(" ","").split(",") ]
            speeds = [ random.uniform(i-std,i+std) for i in speeds ]

            attrs["speed"] = ", ".join([ f"{i}f" for i in speeds ])

        # Mod wattage_per_state
        for i in props:
            if i['id'] == "wattage_per_state" and "std" in i.keys():
                std = float( i.pop("std") )

                watts = [ [ random.uniform(round(float(k)-std, 3), round(float(k)+std, 3)) for k in j.split(":") ] for j in i['value'].replace(" ","").split(",") ]
                watts = ", ".join([ ":".join([ str(k) for k in j ]) for j in watts ])

                i['value'] = watts

        self._generate_subelement(zone, "host", attrs, props)

    def write(self, fat_tree: FatTree):
        assert sum([ int(i["number"]) for i in self.platform["nodes"] ]) == fat_tree.nodes_by_level[0], "Number of nodes of the fat tree does not match the number specified in the platform file"

        platform_xml = xml.Element("platform", attrib=OrderedDict({"version": "4.1"}))
        main_zone = self._generate_subelement(platform_xml, "zone", {"id": "main", "routing": "Full"})

        cluster_compute = self._generate_subelement(main_zone, "zone", {"id": "cluster_compute", "routing": "Full"})

        # Compute nodes
        counter = 0
        for i in self.platform["nodes"]:
            node_type = self.files["nodes"][ i["type"] ]
            node_type["properties"].append({ "id": "type", "value":  i["type"] })

            for j in range( int(i["number"]) ):
                node_type["attributes"]["id"] = fat_tree.nodes[0][j].id

                self._generate_compute_node(cluster_compute, node_type["attributes"], node_type["properties"])
                #self._generate_subelement(cluster_compute, fat_tree.nodes[0][j].type, node_type["attributes"], node_type["properties"])
                counter += 1

        # Routers
        for n in range(1, fat_tree.levels+1):
            for i in fat_tree.nodes[n]:
                self._generate_subelement(cluster_compute, "router", {"id": i.id})
        self._generate_subelement(cluster_compute, "router", {"id": "router_master"})

        # Links
        for i, j in fat_tree.routes.items():
            # Uplinks
            for k in range(j['up']):
                self._generate_subelement(cluster_compute, "link", {"id": i+f"-uplink{k}", "bandwidth": "125MBps", "latency": "100us" })

            # Downlinks
            for k in range(j['dn']):
                self._generate_subelement(cluster_compute, "link", {"id": i+f"-downlink{k}", "bandwidth": "125MBps", "latency": "100us" })

            #self._generate_subelement(cluster_compute, "link", {"id": i, "bandwidth": "125MBps", "latency": "100us" })

        for i in fat_tree.nodes[max(fat_tree.nodes.keys())]:
            self._generate_subelement(cluster_compute, "link", {"id": f"router_master-{i.id}", "bandwidth": "125MBps", "latency": "100us" })

        # Routes
        for i, j in fat_tree.routes.items():
            route = self._generate_subelement(cluster_compute, "route", {"src": j['src'], "dst": j['dst']})
            # Uplinks
            for k in range(j['up']):
                self._generate_subelement(route, "link_ctn", {"id": f"{j['src']}-{j['dst']}-uplink{k}"})

            # Downlinks
            for k in range(j['dn']):
                self._generate_subelement(route, "link_ctn", {"id": f"{j['src']}-{j['dst']}-downlink{k}"})

        for i in fat_tree.nodes[max(fat_tree.nodes.keys())]:
            route = self._generate_subelement(cluster_compute, "route", {"src": "router_master", "dst": i.id})
            self._generate_subelement(route, "link_ctn", {"id": f"router_master-{i.id}"})

        # MASTER ZONE
        self._generate_subelement(main_zone, "cluster", {
            "id": "cluster_master", "prefix": "master_host", "suffix": "", "radical": "0-0", "speed": "100.0Mf",
            "bw": "125MBps", "lat": "50us", "bb_bw": "2.25GBps", "bb_lat": "500us"
            }, [ { "id": "role", "value": "master" } ])

        # CLUSTERS LINK
        self._generate_subelement(main_zone, "link", { "id": "backbone", "bandwidth": "1.25GBps", "latency": "500us" })
        zoneRoute = self._generate_subelement(main_zone, "zoneRoute", { "src": "cluster_compute", "dst": "cluster_master", "gw_src": "router_master", "gw_dst": "master_hostcluster_master_router" })
        self._generate_subelement(zoneRoute, "link_ctn", {"id": f"backbone"})

        def doctype():
            return "<!DOCTYPE platform SYSTEM \"https://simgrid.org/simgrid.dtd\">"

        with open(self.output, "w") as out:
            out.write(xml_format.parseString("{}{}".format(doctype(),
                        xml.tostring(platform_xml).decode())).toprettyxml(indent="    ",
                            encoding="utf-8").decode())

#A = FatTree(2, [4, 4], [2, 2], [1, 2], debug=True)
#A.generate()
#print("--")
#A.draw()

#B = FileInterface("test02.json", "generated.xml")
#B.write(A)

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

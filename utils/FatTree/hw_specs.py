import json
import random
from typing import OrderedDict

import xml.dom.minidom as xml_format
import xml.etree.ElementTree as xml

from platforms import Route
from platforms import Platform
from platforms import Node, NodeType


class PlatformSpecs:
    def __init__(self, input_json: str, output_xml: str = "generated.xml"):
        self.output_xml = output_xml

        with open(input_json, "r") as platform_file:
            self.platform_specs = json.load(platform_file)

        self.files = {}
        # Node types
        with open("node_types.json", "r") as node_file:
            self.files["nodes"] = json.load(node_file)

    def _host_to_xml(self, zone, node: Node):
        def rm_prefix(x: str):
            prefixes = { 'G': 10e9, 'M': 10e6, "k": 10e3 }
            return float(x[:-1]) * prefixes[x[-1]] if x[-1] in prefixes.keys() else float(x)

        # Mod speed
        if "std" in node.attrs.keys():
            std = rm_prefix(node.attrs.pop("std")[:-1])

            speeds = [ rm_prefix(i[:-1]) for i in node.attrs["speed"].replace(" ","").split(",") ]
            speeds = [ round(random.uniform(i-std, i+std),3) for i in speeds ]

            node.attrs["speed"] = ", ".join([ f"{i}f" for i in speeds ])

        # Mod wattage_per_state
        for j in node.props:
            if j["id"] == "wattage_per_state" and "std" in j.keys():
                std = float(j.pop("std"))

                watts = [ k.split(":") for k in j["value"].replace(" ", "").split(",") ]
                watts = [ [ round(random.uniform(float(k)-std, float(k)+std)) for k in n ] for n in watts ]
                watts = ", ".join([ ":".join([ str(k) for k in n ]) for n in watts ])

                j['value'] = watts

        element = xml.SubElement(zone, "host", attrib=OrderedDict(node.attrs))
        for i in node.props:
            xml.SubElement(element, "prop", attrib=OrderedDict(i))

        return element

    def _links_to_xml(self, zone, route: Route):
        assert all( i in route.attrs for i in ["bandwidth", "latency"] ) == True, "Missing attributes in route."

        # Links
        for i in range(route.uplinks):
            curr = route.attrs
            curr["id"] = f"{route.id}-uplink{i}"
            xml.SubElement(zone, "link", attrib=OrderedDict(curr))

        for i in range(route.downlinks):
            curr = route.attrs
            curr["id"] = f"{route.id}-downlink{i}"
            xml.SubElement(zone, "link", attrib=OrderedDict(curr))

    def _route_to_xml(self, zone, route: Route):
        route_el = xml.SubElement(zone, "route", attrib=OrderedDict({"src": route.src, "dst": route.dst}))
        # Uplinks
        for i in range(route.uplinks):
            xml.SubElement(route_el, "link_ctn", attrib=OrderedDict({"id": f"{route.id}-uplink{i}"}))

        for i in range(route.downlinks):
            xml.SubElement(route_el, "link_ctn", attrib=OrderedDict({"id": f"{route.id}-downlink{i}"}))

    def export(self, platform: Platform):
        platform_xml = xml.Element("platform", attrib=OrderedDict({"version": "4.1"}))
        main_zone = xml.SubElement(platform_xml, "zone", attrib=OrderedDict({"id": "main", "routing": "Full"}) )

        cluster_zone = xml.SubElement(main_zone, "zone", attrib=OrderedDict({"id": "cluster_compute", "routing": "Full"}) )

        # Hosts & Routers
        host_types = sum([ [i["type"] for _ in range(i["number"])] for i in self.platform_specs["nodes"] ], [])

        assert len(host_types) == len(platform.nodes_in_level(0)), f"Only {len(host_types)} nodes where provided in the platform input file, {len(platform.nodes_in_level(0))} where expected."
        for i, j in zip(sorted(platform.nodes_in_level(0), key=lambda x: x.node_type), host_types):
            i.props = self.files["nodes"][j]["properties"]
            i.attrs = self.files["nodes"][j]["attributes"]

            i.attrs["id"] = i.id

            self._host_to_xml(cluster_zone, i)

        for i in filter(lambda x: x.level != 0, platform.nodes):
            xml.SubElement(cluster_zone, "router", attrib=OrderedDict({"id": i.id}) )

        # Links
        for i in platform.routes:
            i.attrs = { "bandwidth": "1.25GBps", "latency": "500us" }
            self._links_to_xml(cluster_zone, i)

        # Routes
        for i in platform.routes:
            self._route_to_xml(cluster_zone, i)

        # Master zone
        master_zone = xml.SubElement(main_zone, "cluster", attrib=OrderedDict({
            "id": "cluster_master", "prefix": "master_host", "suffix": "", "radical": "0-0", "speed": "100.0Mf",
            "bw": "125MBps", "lat": "50us", "bb_bw": "2.25GBps", "bb_lat": "500us"
        }))
        xml.SubElement(master_zone, "prop", attrib=OrderedDict({"id": "role", "value": "master"}))

        # Clusters Link
        xml.SubElement(main_zone, "link", attrib=OrderedDict({"id": "backbone", "bandwidth": "1.25GBps", "latency": "500us"}))
        zoneRoute = xml.SubElement(main_zone, "zoneRoute", attrib=OrderedDict({
            "src": "cluster_compute", "dst": "cluster_master",
            "gw_src": "router_master", "gw_dst": "master_hostcluster_master_router"
        }))
        xml.SubElement(zoneRoute, "link_ctn", attrib=OrderedDict({"id": f"backbone"}))

        def doctype():
            return "<!DOCTYPE platform SYSTEM \"https://simgrid.org/simgrid.dtd\">"

        with open(self.output_xml, "w") as out:
            out.write(xml_format.parseString("{}{}".format(doctype(),
                        xml.tostring(platform_xml).decode())).toprettyxml(indent="    ",
                            encoding="utf-8").decode())




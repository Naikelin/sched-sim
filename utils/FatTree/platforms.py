from networkx.drawing.nx_pydot import graphviz_layout
import networkx as nx
from enum import IntEnum

class Platform:
    def __init__(self) -> None:
        self.nodes = list()
        self.routes = set()

    def draw(self) -> None:
        G = nx.DiGraph()

        edges = [ (i.src, i.dst) for i in self.routes if "router_master" not in i.id ]
        G.add_edges_from(edges)

        options = {
            'node_color': 'black',
            'node_size': 100,
            'width': 3,
        }

        pos = graphviz_layout(G, prog="dot")
        nx.draw(G, pos, **options)

class NodeType(IntEnum):
    HOST   = 1
    ROUTER = 2

class Node:
    def __init__(self, id: str, node_type: NodeType):
        self.id = id
        self.node_type = node_type

        self.parents  = list()
        self.children = list()

        self.attrs = dict()
        self.props = list()

    def __str__(self) -> str:
        return f"< {self.node_type} - {self.id} >"

class Route:
    def __init__(self, src: str, dst: str):
        self.src = src
        self.dst = dst

        self.uplinks   = 0
        self.downlinks = 0

        self.attrs = dict()

    @property
    def id(self) -> str:
        return f"{self.src}-{self.dst}"

    def __str__(self) -> str:
        return f"< Route - {self.id} >"

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Route):
            return self.id == other.id
        return False


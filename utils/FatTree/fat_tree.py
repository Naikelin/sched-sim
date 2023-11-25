from itertools import cycle

from platforms import Route
from platforms import Platform
from platforms import Node, NodeType

class FatNode(Node):
    def __init__(self, id: str, node_type: NodeType, level: int):
        super().__init__(id, node_type)
        self.level = level

class FatTree(Platform):
    def __init__(self, levels: int, down: list[int], up: list[int], link_count: list[int]) -> None:
        super().__init__()

        assert levels > 0, "There must be a positive number of levels."
        self.levels = levels

        assert len(down) == levels, f"down must have length {levels}."
        self.down = down

        assert len(up) == levels, f"up must have length {levels}."
        self.up = up

        assert len(link_count) == levels, f"link_count must have length {levels}."
        self.link_count = link_count

        self.build()

    def nodes_in_level(self, n: int) -> list[FatNode]:
        return [ i for i in self.nodes if i.level == n ]

    def _build_hosts(self) -> None:
        """
        Generates the last layer of the tree that belongs to the compute nodes.
        """
        tot_elements = 1
        for i in self.down:
            tot_elements *= i

        for i in range(tot_elements):
            curr = FatNode(f"c{i}", NodeType.HOST, 0)
            self.nodes.append(curr)

    def _build_routers(self, nodes_by_level: list[int]) -> None:
        """
        Generates all the routers needed by the architecture.
        """
        k = 2 * sum(nodes_by_level)
        for i in range(self.levels):
            for j in range(nodes_by_level[i+1]):
                curr = FatNode(f"r{i+1}{j}", NodeType.ROUTER, i+1)
                k -= 1

                self.nodes.append(curr)

    def _build_links(self) -> None:
        """
        Generates all the links between routers and hosts.
        """
        for n in range(1, self.levels+1):
            prev_level = cycle(self.nodes_in_level(n-1))

            for i in self.nodes_in_level(n):
                for j in [ next(prev_level) for _ in range(self.down[i.level-1]) ]:
                    i.children.append(j.id)
                    j.parents.append(i.id)

        for i in self.nodes:
            for j in i.parents:
                curr = Route(j, i.id)
                curr.uplinks   = self.link_count[i.level] if i.level < self.levels else 0
                self.routes.add(curr)

            for j in i.children:
                curr = [k for k in self.routes if k.id == f"{i.id}-{j}"][0]

                if curr in self.routes:
                    curr.downlinks =  self.link_count[ i.level-1 ]
                self.routes.add(curr)

    def _build_master_router(self) -> None:
        router_master = FatNode(f"router_master", NodeType.ROUTER, self.levels+1)

        self.nodes.append(router_master)
        for i in self.nodes_in_level( self.levels ):
            route = Route("router_master", i.id)
            route.uplinks = 1
            route.downlinks = 1

            self.routes.add(route)

    def build(self) -> None:
        self._build_hosts()

        nodes_by_level = [0 for _ in range(self.levels + 1)]
        nodes_by_level[0] = 1
        for i in range(self.levels):
            nodes_by_level[0] *= self.down[i]

        for i in range(self.levels):
            nodes_in_level = 1

            for j in range(i+1):
                nodes_in_level *= self.up[j]

            for j in range(i+1, self.levels):
                nodes_in_level *= self.down[j]

            nodes_by_level[i+1] = nodes_in_level

        self._build_routers(nodes_by_level)
        self._build_links()
        self._build_master_router()

if __name__ == "__main__":
    A = FatTree(2,[4,4],[1,2],[1,2])

    for i in A.nodes:
        print(i, i.level, i.parents, i.children)

    for i in A.routes:
        print(i)


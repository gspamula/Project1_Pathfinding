"""
grid.py
The world the search algorithms run on.

The world is a rectangular grid of cells. Each cell is one of:
    * open ground  (cost 1 to step into)
    * mud          (cost MUD_COST to step into, still walkable)
    * wall         (cannot be entered at all)

Having a terrain cost other than 1 is what makes this project interesting:
breadth first search ignores cost, so it can walk straight through mud,
while Dijkstra and A* go around it when that is cheaper.

AI use: this project is being developed through chats with Claude (Anthropic).
See "AI Use" in README.md. Saved chat logs showing how we worked: AI_CHAT_LOGS.md.
"""

import math
import random

OPEN_COST = 1
MUD_COST = 5
SQRT2 = math.sqrt(2)

# Movement directions as (dx, dy). Orthogonal moves first, then diagonals.
ORTHOGONAL = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAGONAL = [(1, 1), (1, -1), (-1, 1), (-1, -1)]


class Grid:
    """A 2D grid with walls and weighted terrain.

    Cells are addressed as (x, y) tuples where x is the column and y is the row.
    """

    def __init__(self, width, height, allow_diagonal=False):
        self.width = width
        self.height = height
        self.allow_diagonal = allow_diagonal
        self.walls = set()   # cells that cannot be entered
        self.mud = set()     # cells that cost MUD_COST to enter

    # basic queries

    def in_bounds(self, cell):
        x, y = cell
        return 0 <= x < self.width and 0 <= y < self.height

    def passable(self, cell):
        return cell not in self.walls

    def cost(self, cell):
        """Cost of stepping INTO this cell."""
        return MUD_COST if cell in self.mud else OPEN_COST

    def neighbors(self, cell):
        """Yield (neighbor, move_cost) pairs for every legal move out of cell.

        Diagonal moves cost sqrt(2) times the terrain cost, which matches the
        real distance travelled. A diagonal move is only allowed if BOTH
        orthogonal cells beside it are open, so the path never squeezes
        through the corner between two walls.
        """
        x, y = cell
        for dx, dy in ORTHOGONAL:
            nxt = (x + dx, y + dy)
            if self.in_bounds(nxt) and self.passable(nxt):
                yield nxt, self.cost(nxt)

        if not self.allow_diagonal:
            return
        for dx, dy in DIAGONAL:
            nxt = (x + dx, y + dy)
            side_a = (x + dx, y)
            side_b = (x, y + dy)
            if (self.in_bounds(nxt) and self.passable(nxt)
                    and self.passable(side_a) and self.passable(side_b)):
                yield nxt, self.cost(nxt) * SQRT2

    # editing helpers (used by the UI and the benchmark)

    def set_wall(self, cell):
        self.mud.discard(cell)
        self.walls.add(cell)

    def set_mud(self, cell):
        self.walls.discard(cell)
        self.mud.add(cell)

    def clear_cell(self, cell):
        self.walls.discard(cell)
        self.mud.discard(cell)

    def clear(self):
        self.walls.clear()
        self.mud.clear()

    def copy(self):
        g = Grid(self.width, self.height, self.allow_diagonal)
        g.walls = set(self.walls)
        g.mud = set(self.mud)
        return g

    # generators

    def randomize(self, wall_density=0.28, mud_density=0.12, keep_clear=(), rng=None):
        """Scatter random walls and mud. Cells in keep_clear stay open."""
        rng = rng or random
        self.clear()
        keep = set(keep_clear)
        for x in range(self.width):
            for y in range(self.height):
                if (x, y) in keep:
                    continue
                r = rng.random()
                if r < wall_density:
                    self.walls.add((x, y))
                elif r < wall_density + mud_density:
                    self.mud.add((x, y))

    def carve_maze(self, keep_clear=(), rng=None):
        """Build a maze with a randomized depth first search ("recursive backtracker").

        The maze is then opened up a little by knocking out some extra walls,
        so there is more than one route and the algorithms actually differ.
        """
        rng = rng or random
        self.clear()
        self.walls = {(x, y) for x in range(self.width) for y in range(self.height)}

        start = (0, 0)
        self.walls.discard(start)
        stack = [start]
        while stack:
            x, y = stack[-1]
            options = []
            for dx, dy in ORTHOGONAL:
                nx, ny = x + 2 * dx, y + 2 * dy
                if self.in_bounds((nx, ny)) and (nx, ny) in self.walls:
                    options.append((nx, ny, x + dx, y + dy))
            if not options:
                stack.pop()
                continue
            nx, ny, wx, wy = rng.choice(options)
            self.walls.discard((wx, wy))
            self.walls.discard((nx, ny))
            stack.append((nx, ny))

        # Remove about 10% of the remaining walls to create loops.
        for cell in list(self.walls):
            if rng.random() < 0.10:
                self.walls.discard(cell)
        for cell in keep_clear:
            self.walls.discard(cell)

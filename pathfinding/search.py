"""
search.py
BFS, Dijkstra, Greedy Best First, and A*, written as ONE best first search.

All four algorithms follow the same loop:

    1. put the start cell in the frontier (a priority queue)
    2. pop the cell with the LOWEST priority
    3. if it is the goal, rebuild the path and stop
    4. otherwise look at its neighbors, record a better route to any of
       them, and push them into the frontier
    5. repeat until the frontier is empty (no path exists)

The ONLY difference between the algorithms is what "priority" means:

    algorithm   priority          what it cares about
    ----------  ----------------  ------------------------------------------
    BFS         steps so far      fewest moves; ignores terrain cost
    Dijkstra    g                 cheapest cost so far; no sense of direction
    Greedy      h                 closest looking to the goal; ignores cost
    A*          g + w * h         cost so far PLUS an estimate of cost left

where g = actual cost from the start, h = heuristic estimate to the goal,
and w = heuristic weight (1 for normal A*, >1 for "weighted A*").

This is the whole story of "A* is an evolution of BFS and Dijkstra":
BFS -> add edge costs -> Dijkstra -> add a heuristic -> A*.

The search is written as a Python GENERATOR. Each time it expands a cell it
`yield`s a SearchStep, so the PyGame visualizer can draw the search one step
at a time. `run_search` just runs the generator to the end for the benchmark.

AI use: written with help from Claude (Anthropic). See "AI Use" in README.md.
"""

import heapq
import itertools
import time
from dataclasses import dataclass, field

from .heuristics import zero

ALGORITHMS = ["A*", "Dijkstra", "BFS", "Greedy"]


@dataclass
class SearchStep:
    """A snapshot sent to the visualizer after each expansion."""
    current: tuple
    frontier: set
    closed: set


@dataclass
class SearchResult:
    path: list = field(default_factory=list)  # list of cells, start..goal ([] if none)
    cost: float = float("inf")                # total terrain cost of the path
    expanded: int = 0                         # how many cells were popped and processed
    max_frontier: int = 0                     # largest size the open set reached (memory)
    elapsed_ms: float = 0.0
    found: bool = False
    closed: set = field(default_factory=set)
    frontier: set = field(default_factory=set)


def reconstruct_path(came_from, goal):
    """Follow parent pointers backwards from the goal, then reverse."""
    path = [goal]
    while came_from[path[-1]] is not None:
        path.append(came_from[path[-1]])
    path.reverse()
    return path


def search_steps(grid, start, goal, algorithm="A*", heuristic=zero, weight=1.0):
    """Generator version of the search. Yields SearchStep, returns SearchResult.

    Usage:
        gen = search_steps(...)
        try:
            while True: step = next(gen)
        except StopIteration as done:
            result = done.value
    """
    if algorithm not in ALGORITHMS:
        raise ValueError(f"unknown algorithm {algorithm!r}")

    t0 = time.perf_counter()
    result = SearchResult()

    # Edge cases: bad endpoints means there is nothing to search.
    if not (grid.in_bounds(start) and grid.in_bounds(goal)):
        return result
    if not (grid.passable(start) and grid.passable(goal)):
        return result

    def h(cell):
        return heuristic(cell, goal, start)

    def priority(cell):
        """The one line that turns this loop into BFS, Dijkstra, Greedy, or A*."""
        if algorithm == "BFS":
            return steps[cell]
        if algorithm == "Dijkstra":
            return g[cell]
        if algorithm == "Greedy":
            return h(cell)
        return g[cell] + weight * h(cell)          # A*

    g = {start: 0.0}           # best known cost from start to each cell
    steps = {start: 0}         # number of moves on that best route (for BFS)
    came_from = {start: None}  # parent pointers used to rebuild the path
    closed = set()             # cells that are finished

    # Heap entries are (priority, tiebreak_h, counter, cell).
    #   tiebreak_h: when two cells have equal priority, prefer the one that
    #               looks closer to the goal (fewer wasted expansions).
    #   counter:    keeps equal entries first in, first out, and stops Python
    #               from ever comparing two cell tuples.
    counter = itertools.count()
    frontier = [(priority(start), h(start), next(counter), start)]
    in_frontier = {start}

    while frontier:
        _, _, _, current = heapq.heappop(frontier)

        # "Lazy deletion": a cell can be pushed more than once when we find a
        # better route to it. Only the first (best) copy popped matters.
        if current in closed:
            continue
        closed.add(current)
        in_frontier.discard(current)
        result.expanded += 1

        if current == goal:
            result.path = reconstruct_path(came_from, goal)
            result.cost = g[goal]
            result.found = True
            break

        for nxt, move_cost in grid.neighbors(current):
            if nxt in closed:
                continue
            new_g = g[current] + move_cost
            new_steps = steps[current] + 1

            # BFS judges routes by number of moves; everything else by cost.
            if algorithm == "BFS":
                better = nxt not in steps or new_steps < steps[nxt]
            else:
                better = nxt not in g or new_g < g[nxt]

            if better:
                g[nxt] = new_g
                steps[nxt] = new_steps
                came_from[nxt] = current
                heapq.heappush(frontier, (priority(nxt), h(nxt), next(counter), nxt))
                in_frontier.add(nxt)

        result.max_frontier = max(result.max_frontier, len(in_frontier))
        yield SearchStep(current, in_frontier, closed)

    result.elapsed_ms = (time.perf_counter() - t0) * 1000
    result.closed = closed
    result.frontier = in_frontier
    return result


def run_search(grid, start, goal, algorithm="A*", heuristic=zero, weight=1.0):
    """Run a search to completion and return only the SearchResult."""
    gen = search_steps(grid, start, goal, algorithm, heuristic, weight)
    while True:
        try:
            next(gen)
        except StopIteration as done:
            return done.value

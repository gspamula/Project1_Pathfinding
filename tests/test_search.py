"""
Edge case and correctness tests. Run with:  python -m pytest

AI use: written with help from Claude (Anthropic). See "AI Use" in README.md.
"""

import math
import random

import pytest

from pathfinding.grid import Grid, MUD_COST
from pathfinding.heuristics import (manhattan, euclidean, chebyshev, octile,
                                    tiebreak_octile, zero)
from pathfinding.search import run_search

ADMISSIBLE_4 = [zero, manhattan, euclidean, chebyshev, octile]
ADMISSIBLE_8 = [zero, euclidean, chebyshev, octile]


def test_start_equals_goal():
    g = Grid(5, 5)
    r = run_search(g, (2, 2), (2, 2), "A*", manhattan)
    assert r.found and r.path == [(2, 2)] and r.cost == 0


def test_no_path_when_goal_walled_in():
    g = Grid(5, 5)
    for c in [(3, 2), (1, 2), (2, 1), (2, 3)]:
        g.set_wall(c)
    r = run_search(g, (0, 0), (2, 2), "A*", manhattan)
    assert not r.found and r.path == []


def test_blocked_start_or_goal():
    g = Grid(5, 5)
    g.set_wall((4, 4))
    assert not run_search(g, (0, 0), (4, 4), "A*", manhattan).found
    assert not run_search(g, (4, 4), (0, 0), "A*", manhattan).found


def test_out_of_bounds():
    g = Grid(5, 5)
    assert not run_search(g, (0, 0), (9, 9), "A*", manhattan).found


def test_no_corner_cutting():
    # Two walls touching at a corner: the diagonal between them is illegal.
    g = Grid(2, 2, allow_diagonal=True)
    g.set_wall((1, 0))
    g.set_wall((0, 1))
    assert not run_search(g, (0, 0), (1, 1), "A*", octile).found


def test_astar_avoids_mud_but_bfs_does_not():
    # A mud strip on the direct route; a detour around costs less.
    # Mud at (3,0): straight = 5 open steps + 1 mud step = 10.
    # Detour = down 1, right 6, up 1 = 8 open steps.
    g = Grid(7, 2)
    g.set_mud((3, 0))
    bfs = run_search(g, (0, 0), (6, 0), "BFS")
    astar = run_search(g, (0, 0), (6, 0), "A*", manhattan)
    assert astar.cost < bfs.cost
    assert astar.cost == 8          # detour through row 2 (8 open steps)
    assert bfs.cost == 6 + MUD_COST - 1  # straight through the mud


def _random_grid(seed, diagonal):
    rng = random.Random(seed)
    g = Grid(25, 20, allow_diagonal=diagonal)
    g.randomize(0.28, 0.12, keep_clear=[(0, 0), (24, 19)], rng=rng)
    return g


@pytest.mark.parametrize("seed", range(40))
def test_admissible_heuristics_are_optimal_4dir(seed):
    g = _random_grid(seed, diagonal=False)
    best = run_search(g, (0, 0), (24, 19), "Dijkstra")
    for h in ADMISSIBLE_4:
        r = run_search(g, (0, 0), (24, 19), "A*", h)
        assert r.found == best.found
        if best.found:
            assert math.isclose(r.cost, best.cost), h.__name__


@pytest.mark.parametrize("seed", range(40))
def test_admissible_heuristics_are_optimal_8dir(seed):
    g = _random_grid(seed, diagonal=True)
    best = run_search(g, (0, 0), (24, 19), "Dijkstra")
    for h in ADMISSIBLE_8:
        r = run_search(g, (0, 0), (24, 19), "A*", h)
        assert r.found == best.found
        if best.found:
            assert math.isclose(r.cost, best.cost), h.__name__


@pytest.mark.parametrize("seed", range(40))
def test_better_heuristic_expands_fewer_cells(seed):
    g = _random_grid(seed, diagonal=False)
    dij = run_search(g, (0, 0), (24, 19), "Dijkstra")
    man = run_search(g, (0, 0), (24, 19), "A*", manhattan)
    assert man.expanded <= dij.expanded


def test_tiebreak_is_near_optimal():
    for seed in range(40):
        g = _random_grid(seed, diagonal=True)
        best = run_search(g, (0, 0), (24, 19), "Dijkstra")
        r = run_search(g, (0, 0), (24, 19), "A*", tiebreak_octile)
        if best.found:
            assert r.cost <= best.cost * 1.01


def test_path_is_connected_and_legal():
    g = _random_grid(3, diagonal=True)
    r = run_search(g, (0, 0), (24, 19), "A*", octile)
    if not r.found:
        return
    for a, b in zip(r.path, r.path[1:]):
        assert b in dict(g.neighbors(a))

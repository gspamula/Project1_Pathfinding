"""
heuristics.py
Heuristic functions for A*.

A heuristic h(n) is a GUESS of the remaining cost from cell n to the goal.
Every function here has the same signature:

    h(node, goal, start) -> float

`start` is only used by the tie breaking heuristic, but passing it to all of
them keeps the search code simple.

Two properties matter:
    * ADMISSIBLE: h never overestimates the true remaining cost.
      If h is admissible, A* is guaranteed to find the shortest path.
    * CONSISTENT: h(n) <= cost(n, m) + h(m) for every neighbor m.
      Consistent implies admissible, and it means A* never has to reopen
      a cell it already finished.

Because the cheapest possible step in our grid costs 1 (open ground), a
distance measured in cells is a safe lower bound on cost. Mud only makes
the true cost bigger, so none of these ever overestimate because of mud.

Which heuristic is admissible depends on how the agent may move:

    heuristic   | 4 direction moves      | 8 direction moves (diag = sqrt 2)
    ------------+------------------------+-----------------------------------
    zero        | admissible (=Dijkstra) | admissible (=Dijkstra)
    manhattan   | admissible, EXACT fit  | NOT admissible (overestimates)
    euclidean   | admissible, weak       | admissible, a bit weak
    chebyshev   | admissible, weakest    | admissible, weak
    octile      | admissible, weak       | admissible, EXACT fit
    tiebreak    | ~admissible            | ~admissible (tiny nudge, see below)

AI use: written with help from Claude (Anthropic). See "AI Use" in README.md.
"""

import math

SQRT2 = math.sqrt(2)


def zero(node, goal, start=None):
    """h = 0. A* with this heuristic behaves exactly like Dijkstra."""
    return 0.0


def manhattan(node, goal, start=None):
    """|dx| + |dy|. The true distance on an empty grid with 4 direction moves."""
    return abs(node[0] - goal[0]) + abs(node[1] - goal[1])


def euclidean(node, goal, start=None):
    """Straight line distance. Never overestimates, but underestimates on a grid,
    so A* explores more cells than it needs to."""
    return math.hypot(node[0] - goal[0], node[1] - goal[1])


def chebyshev(node, goal, start=None):
    """max(|dx|, |dy|). The true distance if a diagonal step cost 1.
    Our diagonals cost sqrt(2), so this is a loose (weak) underestimate."""
    return max(abs(node[0] - goal[0]), abs(node[1] - goal[1]))


def octile(node, goal, start=None):
    """Take as many diagonal steps as possible, then go straight.
    diag steps = min(dx, dy), straight steps = max - min.
    cost = min*sqrt2 + (max - min) = max + (sqrt2 - 1) * min
    This is the exact distance on an empty 8 direction grid."""
    dx = abs(node[0] - goal[0])
    dy = abs(node[1] - goal[1])
    return max(dx, dy) + (SQRT2 - 1) * min(dx, dy)


def tiebreak_octile(node, goal, start=None):
    """Octile distance plus a tiny cross product nudge (idea from Red Blob Games).

    On open ground MANY cells have the same f = g + h value, and A* wastes
    time exploring all of them. The cross product measures how far `node`
    is from the straight line between start and goal. Adding a very small
    multiple of it breaks ties in favor of cells on that line, so the search
    runs straight at the goal.

    The nudge is scaled to 0.001 per unit, so the path can be at most a tiny
    fraction longer than optimal. In practice it almost always stays optimal.
    """
    h = octile(node, goal)
    if start is None:
        return h
    dx1, dy1 = node[0] - goal[0], node[1] - goal[1]
    dx2, dy2 = start[0] - goal[0], start[1] - goal[1]
    cross = abs(dx1 * dy2 - dx2 * dy1)
    return h + cross * 0.001


# Registry used by the UI and the benchmark: name -> function
HEURISTICS = {
    "Manhattan": manhattan,
    "Euclidean": euclidean,
    "Chebyshev": chebyshev,
    "Octile": octile,
    "Octile + tiebreak": tiebreak_octile,
    "Zero (Dijkstra)": zero,
}

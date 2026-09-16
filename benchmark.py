"""
benchmark.py
Heuristic experiment: run every algorithm/heuristic on many random maps and
measure speed (cells expanded, time) and accuracy (how close to the cheapest path).

Run:  python benchmark.py            (default 300 maps per movement mode)
      python benchmark.py --maps 50  (faster)

Writes results/benchmark_results.csv and results/benchmark_results.md.
Dijkstra is the "ground truth" because it always finds the cheapest path.

AI use: written with help from Claude (Anthropic). See "AI Use" in README.md.
"""

import argparse
import csv
import os
import random
import statistics

from pathfinding.grid import Grid
from pathfinding.heuristics import HEURISTICS, manhattan, octile
from pathfinding.search import run_search

WIDTH, HEIGHT = 40, 33

# (label, algorithm, heuristic function, weight)
CONFIGS = [
    ("BFS", "BFS", HEURISTICS["Zero (Dijkstra)"], 1.0),
    ("Dijkstra", "Dijkstra", HEURISTICS["Zero (Dijkstra)"], 1.0),
    ("A* Zero", "A*", HEURISTICS["Zero (Dijkstra)"], 1.0),
    ("A* Manhattan", "A*", HEURISTICS["Manhattan"], 1.0),
    ("A* Euclidean", "A*", HEURISTICS["Euclidean"], 1.0),
    ("A* Chebyshev", "A*", HEURISTICS["Chebyshev"], 1.0),
    ("A* Octile", "A*", HEURISTICS["Octile"], 1.0),
    ("A* Octile + tiebreak", "A*", HEURISTICS["Octile + tiebreak"], 1.0),
    ("Weighted A* Manhattan w=1.5", "A*", manhattan, 1.5),
    ("Weighted A* Manhattan w=2", "A*", manhattan, 2.0),
    ("Weighted A* Octile w=1.5", "A*", octile, 1.5),
    ("Weighted A* Octile w=2", "A*", octile, 2.0),
    ("Weighted A* Octile w=5", "A*", octile, 5.0),
    ("Greedy Manhattan", "Greedy", manhattan, 1.0),
    ("Greedy Octile", "Greedy", octile, 1.0),
]


def random_problem(rng, diagonal):
    """A random map with start and goal in opposite regions of the grid."""
    start = (rng.randrange(0, 8), rng.randrange(HEIGHT))
    goal = (rng.randrange(WIDTH - 8, WIDTH), rng.randrange(HEIGHT))
    g = Grid(WIDTH, HEIGHT, allow_diagonal=diagonal)
    g.randomize(wall_density=0.28, mud_density=0.12, keep_clear=[start, goal], rng=rng)
    return g, start, goal


def run(maps, seed):
    rows = []
    for diagonal in (False, True):
        rng = random.Random(seed)
        stats = {label: {"expanded": [], "ms": [], "ratio": [], "optimal": 0, "max_open": []}
                 for label, *_ in CONFIGS}
        solved = 0
        while solved < maps:
            grid, start, goal = random_problem(rng, diagonal)
            truth = run_search(grid, start, goal, "Dijkstra")
            if not truth.found:
                continue  # skip unsolvable maps; they would just measure "search everything"
            solved += 1
            for label, algo, h, w in CONFIGS:
                r = run_search(grid, start, goal, algo, h, w)
                s = stats[label]
                s["expanded"].append(r.expanded)
                s["ms"].append(r.elapsed_ms)
                s["max_open"].append(r.max_frontier)
                s["ratio"].append(r.cost / truth.cost)
                if abs(r.cost - truth.cost) < 1e-9:
                    s["optimal"] += 1

        dij = statistics.mean(stats["Dijkstra"]["expanded"])
        for label, *_ in CONFIGS:
            s = stats[label]
            exp = statistics.mean(s["expanded"])
            rows.append({
                "movement": "8 way" if diagonal else "4 way",
                "method": label,
                "avg_expanded": round(exp, 1),
                "vs_dijkstra": f"{exp / dij * 100:.0f}%",
                "avg_max_open": round(statistics.mean(s["max_open"]), 1),
                "avg_ms": round(statistics.mean(s["ms"]), 3),
                "optimal_pct": f"{s['optimal'] / maps * 100:.1f}%",
                "avg_cost_ratio": round(statistics.mean(s["ratio"]), 4),
                "worst_cost_ratio": round(max(s["ratio"]), 4),
            })
    return rows


def write(rows, maps, seed):
    os.makedirs("results", exist_ok=True)
    with open("results/benchmark_results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    cols = ["method", "avg_expanded", "vs_dijkstra", "avg_ms", "optimal_pct",
            "avg_cost_ratio", "worst_cost_ratio"]
    lines = [f"# Benchmark results",
             "",
             f"{maps} solvable random {WIDTH}x{HEIGHT} maps per movement mode "
             f"(28% walls, 12% mud, seed {seed}).",
             "cost ratio = path cost / Dijkstra's cost (1.0 means optimal).", ""]
    for mode in ("4 way", "8 way"):
        lines += [f"## {mode} movement", "",
                  "| " + " | ".join(cols) + " |",
                  "|" + "---|" * len(cols)]
        for r in rows:
            if r["movement"] == mode:
                lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
        lines.append("")
    with open("results/benchmark_results.md", "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--maps", type=int, default=300)
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()
    write(run(args.maps, args.seed), args.maps, args.seed)

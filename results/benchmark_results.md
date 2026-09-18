# Benchmark results

300 solvable random 40x33 maps per movement mode (28% walls, 12% mud, seed 2026).
cost ratio = path cost / Dijkstra's cost (1.0 means optimal).

## 4 way movement

| method | avg_expanded | vs_dijkstra | avg_ms | optimal_pct | avg_cost_ratio | worst_cost_ratio |
|---|---|---|---|---|---|---|
| BFS | 790.8 | 102% | 2.674 | 1.7% | 1.3027 | 1.8387 |
| Dijkstra | 778.2 | 100% | 2.68 | 100.0% | 1.0 | 1.0 |
| A* Zero | 778.2 | 100% | 2.506 | 100.0% | 1.0 | 1.0 |
| A* Manhattan | 350.7 | 45% | 1.322 | 100.0% | 1.0 | 1.0 |
| A* Euclidean | 486.6 | 63% | 1.835 | 100.0% | 1.0 | 1.0 |
| A* Chebyshev | 517.3 | 66% | 1.909 | 100.0% | 1.0 | 1.0 |
| A* Octile | 466.7 | 60% | 1.88 | 100.0% | 1.0 | 1.0 |
| A* Octile + tiebreak | 461.6 | 59% | 2.125 | 100.0% | 1.0 | 1.0 |
| Weighted A* Manhattan w=1.5 | 191.3 | 25% | 0.743 | 61.7% | 1.021 | 1.1395 |
| Weighted A* Manhattan w=2 | 125.9 | 16% | 0.551 | 20.7% | 1.0892 | 1.4681 |
| Weighted A* Octile w=1.5 | 260.1 | 33% | 1.173 | 87.3% | 1.0051 | 1.0741 |
| Weighted A* Octile w=2 | 151.7 | 19% | 0.672 | 54.0% | 1.0328 | 1.25 |
| Weighted A* Octile w=5 | 77.2 | 10% | 0.364 | 5.7% | 1.2056 | 1.7213 |
| Greedy Manhattan | 75.7 | 10% | 0.306 | 1.0% | 1.4044 | 2.1692 |
| Greedy Octile | 70.5 | 9% | 0.33 | 1.3% | 1.4002 | 2.5692 |

## 8 way movement

| method | avg_expanded | vs_dijkstra | avg_ms | optimal_pct | avg_cost_ratio | worst_cost_ratio |
|---|---|---|---|---|---|---|
| BFS | 797.6 | 103% | 3.759 | 1.0% | 1.3237 | 1.78 |
| Dijkstra | 774.5 | 100% | 3.789 | 100.0% | 1.0 | 1.0 |
| A* Zero | 774.5 | 100% | 3.852 | 100.0% | 1.0 | 1.0 |
| A* Manhattan | 312.0 | 40% | 1.777 | 72.0% | 1.0054 | 1.0668 |
| A* Euclidean | 429.0 | 55% | 2.434 | 100.0% | 1.0 | 1.0 |
| A* Chebyshev | 475.8 | 61% | 2.729 | 100.0% | 1.0 | 1.0 |
| A* Octile | 397.4 | 51% | 2.439 | 100.0% | 1.0 | 1.0 |
| A* Octile + tiebreak | 393.6 | 51% | 2.747 | 100.0% | 1.0 | 1.0 |
| Weighted A* Manhattan w=1.5 | 159.3 | 21% | 1.086 | 23.0% | 1.0506 | 1.4033 |
| Weighted A* Manhattan w=2 | 112.0 | 14% | 0.65 | 6.7% | 1.1084 | 1.6447 |
| Weighted A* Octile w=1.5 | 204.3 | 26% | 1.316 | 40.0% | 1.0184 | 1.1101 |
| Weighted A* Octile w=2 | 126.1 | 16% | 0.817 | 13.0% | 1.0637 | 1.4106 |
| Weighted A* Octile w=5 | 71.0 | 9% | 0.47 | 2.7% | 1.2098 | 1.7528 |
| Greedy Manhattan | 71.4 | 9% | 0.412 | 0.3% | 1.4226 | 2.2657 |
| Greedy Octile | 64.9 | 8% | 0.417 | 0.3% | 1.4295 | 2.3276 |

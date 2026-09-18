# Project 1: A* Pathfinding Exploration

ADV Machine Learning and AI, Mr. Cochran

An A* pathfinding implementation written from scratch in Python, with a live PyGame visualizer and a benchmark that measures how different heuristics trade speed for accuracy. BFS, Dijkstra, and Greedy Best First Search are included for comparison.

![A* with the octile heuristic on a random map with walls and mud](results/screenshot.png)

## Quick start

```bash
pip install -r requirements.txt
python main.py             # interactive visualizer (same as python visualizer.py)
python benchmark.py         # heuristic experiment (writes results/)
python -m pytest            # 128 correctness and edge case tests
```

In PyCharm: open the folder, set the interpreter to Python 3.10 or newer, install the requirements, then right click `main.py` and choose Run.

## Project layout

| File | What it does |
|---|---|
| `main.py` | Entry point; opens the visualizer |
| `pathfinding/grid.py` | The world: walls, mud (cost 5), 4 way or 8 way movement, random map and maze generators |
| `pathfinding/heuristics.py` | Six heuristic functions and notes on when each one is admissible |
| `pathfinding/search.py` | One best first search loop that becomes BFS, Dijkstra, Greedy, or A* |
| `visualizer.py` | PyGame UI that animates the search in real time |
| `window.py` | Opens a window that stays sharp on high resolution (Retina) screens |
| `benchmark.py` | Runs every method on 300 random maps per movement mode |
| `tests/test_search.py` | Edge cases and optimality checks |
| `results/` | Benchmark output (`.md` and `.csv`) and a screenshot |
| `AI_CHAT_LOGS.md` and `2026-09-*.md` | Chat logs of the AI sessions on this project (Honor Code documentation) |

## How A* works

A* keeps a **frontier** (priority queue) of cells to look at next. It repeatedly takes out the cell with the lowest score

```
f(n) = g(n) + h(n)
```

* **g(n)** is the real cost of the best route found so far from the start to n
* **h(n)** is the heuristic, a guess of the cost still left from n to the goal

When the goal comes out of the queue, A* follows parent pointers back to the start to rebuild the path. If the queue empties first, no path exists.

### From BFS to Dijkstra to A*

`search.py` uses the same loop for all four algorithms. Only the priority changes:

| Algorithm | Priority | Strength | Weakness |
|---|---|---|---|
| BFS | number of steps | fewest moves; simple | ignores terrain cost, so it walks straight through mud |
| Dijkstra | g | always cheapest path | no sense of direction; spreads out in every direction |
| Greedy Best First | h | very fast | ignores cost so far; paths are often much worse |
| **A\*** | **g + h** | cheapest path **and** aimed at the goal | only as good as its heuristic |

So A* is an evolution of the earlier two: BFS plus edge costs gives Dijkstra, and Dijkstra plus a heuristic gives A*. With h = 0, A* *is* Dijkstra (the benchmark confirms both expand exactly the same number of cells).

### Admissible and consistent heuristics

* **Admissible:** h never overestimates the real remaining cost. Then A* is guaranteed to find the cheapest path.
* **Consistent:** h(n) ≤ cost(n, m) + h(m) for every neighbor m. Then A* never needs to reopen a finished cell, which is why `search.py` can skip anything already in `closed`.

The cheapest step in this grid costs 1, so distances measured in cells never overestimate. Mud only makes the real cost larger.

Manhattan with diagonal moves, weighted A\*, and (by a tiny amount) the tiebreak nudge are **not** consistent. For those, skipping closed cells can make the path a little worse than optimal. That is a deliberate trade: reopening cells would cost extra work, and the benchmark measures exactly how much accuracy is lost.

## Heuristic choices

| Heuristic | Formula | 4 way | 8 way (diagonal costs √2) |
|---|---|---|---|
| Zero | 0 | admissible (same as Dijkstra) | admissible |
| Manhattan | dx + dy | admissible and exact on open ground | **overestimates** a diagonal (2 vs 1.41) |
| Euclidean | √(dx² + dy²) | admissible but loose | admissible but loose |
| Chebyshev | max(dx, dy) | admissible, loosest | admissible, loose (treats diagonal as cost 1) |
| Octile | max + (√2 − 1)·min | admissible | admissible and exact on open ground |
| Octile + tiebreak | octile + 0.001 × cross product | ≈ admissible | ≈ admissible |

**Why these?** The best heuristic is the one that matches how the agent actually moves. Manhattan is the exact open ground distance for 4 way movement and octile is the exact distance for 8 way movement. The closer h is to the real cost (without going over), the fewer cells A* has to explore. Euclidean and Chebyshev are included to show what happens when a heuristic is safe but weak.

**Tiebreak heuristic (custom).** On open ground many cells share the same f value and A* explores all of them. The tiebreak version adds a tiny amount based on how far a cell is from the straight line between start and goal (a cross product), so ties go to cells on that line. The nudge is small enough that it matched Dijkstra's cost on all 600 benchmark maps. The search also breaks ties in the priority queue by preferring the cell with the smaller h.

**Weighted A\*.** Using f = g + w·h with w > 1 makes the heuristic count more. That makes it inadmissible, so A* can return a longer path, but it explores far fewer cells. When h is consistent (Manhattan for 4 way, octile for 8 way), the path is guaranteed to cost at most w times the optimal cost. The benchmark agrees: with those heuristics the worst case at w = 2 was 1.47× optimal. Press `[` and `]` in the visualizer to try it.

## Implementation decisions

* **One loop, four algorithms.** BFS, Dijkstra, Greedy, and A* share the loop in `search.py`; only the `priority()` function changes. This makes the comparison fair (same data structures, same tie breaking), and it shows directly in the code how A* grows out of the other two.
* **The search is a generator.** `search_steps` pauses (`yield`) after every expansion. The visualizer pulls a few steps per frame to animate, and the benchmark and tests run the very same code to the end with `run_search`. The algorithm contains no drawing code.
* **Goal test when a cell is popped, not when it is pushed.** With costs other than 1, the first route found to the goal is not always the cheapest. Waiting until the goal comes off the queue is what guarantees the cheapest path.
* **Lazy deletion instead of decrease key.** Python's `heapq` cannot lower the priority of an item already in the queue. When a cheaper route to a cell is found, the cell is pushed again and the old, worse copy is skipped when it is popped (it is already in `closed`).
* **Heap entries are `(priority, h, counter, cell)`.** If two cells have equal priority, the one with smaller h (closer to the goal) goes first, which saves expansions. The counter keeps equal entries first in, first out and stops Python from ever comparing two cells.
* **Mud costs 5 and diagonals cost √2.** On a 4 way grid with no mud every step costs 1, so BFS and Dijkstra would always find equally cheap paths. Mud is what makes the difference between them visible. Diagonals cost √2 because that is the real distance, which is also why octile is the right heuristic for 8 way movement.
* **No corner cutting.** A diagonal step is allowed only if both cells beside it are open, so paths never slip between two walls that touch at a corner.
* **A sharp window on Retina screens.** PyGame normally draws at 1 pixel per screen point, and macOS stretches that 2× on a Retina display, which made the visualizer blurry. pygame 2.6 never passes SDL's "high DPI" flag, so `window.py` creates the window through SDL directly, draws on a canvas at the real pixel size, and copies it to the screen. Everywhere else it falls back to a normal pygame window.
* **Dijkstra is the ground truth.** In the benchmark every method is compared against Dijkstra's cost on the same map. Unsolvable maps are skipped, because every method just searches the whole reachable area on them.

## Results

Averages over 300 solvable random 40×33 maps per mode (28% walls, 12% mud). "Expanded" is how many cells the search processed. "Optimal" is how often the path cost matched Dijkstra. Full tables are in [`results/benchmark_results.md`](results/benchmark_results.md).

**4 way movement**

| Method | Expanded | vs Dijkstra | Optimal | Worst cost ratio |
|---|---|---|---|---|
| BFS | 791 | 102% | 1.7% | 1.84 |
| Dijkstra | 778 | 100% | 100% | 1.00 |
| A* Manhattan | **351** | **45%** | **100%** | 1.00 |
| A* Octile | 467 | 60% | 100% | 1.00 |
| A* Euclidean | 487 | 63% | 100% | 1.00 |
| A* Chebyshev | 517 | 66% | 100% | 1.00 |
| Weighted A* Manhattan w=1.5 | 191 | 25% | 61.7% | 1.14 |
| Weighted A* Manhattan w=2 | 126 | 16% | 20.7% | 1.47 |
| Greedy Manhattan | 76 | 10% | 1.0% | 2.17 |

**8 way movement**

| Method | Expanded | vs Dijkstra | Optimal | Worst cost ratio |
|---|---|---|---|---|
| BFS | 798 | 103% | 1.0% | 1.78 |
| Dijkstra | 775 | 100% | 100% | 1.00 |
| A* Manhattan | 312 | 40% | **72.0%** | 1.07 |
| A* Octile | **397** | **51%** | **100%** | 1.00 |
| A* Octile + tiebreak | 394 | 51% | 100% | 1.00 |
| A* Euclidean | 429 | 55% | 100% | 1.00 |
| A* Chebyshev | 476 | 61% | 100% | 1.00 |
| Weighted A* Octile w=1.5 | 204 | 26% | 40.0% | 1.11 |
| Weighted A* Octile w=2 | 126 | 16% | 13.0% | 1.41 |
| Greedy Octile | 65 | 8% | 0.3% | 2.33 |

### What the numbers show

1. **A heuristic that fits the movement rules wins.** Manhattan is best for 4 way movement (55% fewer cells than Dijkstra, always optimal). Octile is best among the safe choices for 8 way movement.
2. **An overestimating heuristic breaks the optimality guarantee.** With diagonals on, Manhattan looks faster (312 cells) but misses the cheapest path on 28% of maps.
3. **Tighter is better.** Chebyshev < Euclidean < Octile in how close they are to the real cost, and the number of expanded cells goes down in that order.
4. **Speed versus accuracy is a dial.** Weight 1.5 cuts the work roughly in half again, and its paths cost at most 14% more than optimal. Weight 5 and Greedy expand only about a tenth as many cells as Dijkstra, but weight 5 paths can cost up to 75% more and Greedy paths more than twice as much.
5. **BFS is not optimal once terrain has costs.** It finds the fewest moves, which usually means wading through mud.
6. **The tiebreak helps only a little here** (about 1%) because 28% walls leave few long open stretches. It helps much more on an empty map: from (2, 5) to (37, 28) with diagonals on, plain octile expands 66 cells and the tiebreak version only 36, for the same path cost. You can see this in the visualizer by pressing `C` and then running.

## Visualizer controls

| Input | Action |
|---|---|
| Left drag | draw walls |
| Shift + left drag | paint mud |
| Right drag | erase |
| `S` / `E` | move start / end to the mouse |
| `SPACE` | run or pause |
| `N` | step one expansion |
| `R` | reset search, keep the map |
| `C` | clear the map |
| `G` / `M` | random map / maze |
| `A` | cycle algorithm (A*, Dijkstra, BFS, Greedy) |
| `H` | cycle heuristic |
| `D` | toggle diagonal movement |
| `[` / `]` | heuristic weight down / up |
| `-` / `=` | animation speed |
| `TAB` | run every method on the current map and show a comparison table (red rows are not the cheapest path) |

Colors: green = open (frontier), blue = explored (closed), with lighter blue expanded earlier and darker blue later, so you can watch the search spread out. Orange = cell being expanded, yellow line = final path, brown = mud, dark = wall.

The side panel shows each setting next to the key that changes it, and explains the current algorithm and heuristic in plain English. It warns in red when a heuristic can overestimate (Manhattan with diagonal moves) and in yellow when a weight above 1 trades accuracy for speed. The panel also shows live stats, and pressing `TAB` adds the comparison table, where each bar is the number of cells explored. The window picks its cell size so everything fits on a laptop screen.

## Edge cases handled

* Start equals goal (path of one cell, cost 0)
* Start or goal is a wall or out of bounds (no path)
* Goal completely walled in (search empties the frontier and reports no path)
* No squeezing diagonally between two walls that touch at a corner
* Duplicate queue entries after finding a cheaper route (skipped with lazy deletion)
* Mud cells are drawn on top of the explored color so the terrain stays visible

## Testing

```bash
python -m pytest -q
```

The tests check the edge cases above, check that every admissible heuristic matches Dijkstra's cost on 40 random maps in each movement mode, check that A* Manhattan never expands more cells than Dijkstra, and check that every step in a returned path is a legal move.

## Resources

* Red Blob Games, *Introduction to the A\* Algorithm* and *Heuristics* pages (cross product tie breaking idea)
* GeeksforGeeks, *A\* Search Algorithm*
* Codementor, *Basic Pathfinding Explained with Python*

## AI Use

As required by the Durham Academy Honor Code, here is how AI was used on this project.

**How this project is written:** it is being developed through chats with Claude in the Claude desktop app. I say what I want (for example, checking the project against the rubric or fixing a blurry window), and Claude explains, proposes changes, and makes them in the code. Saved chat logs showing how we worked are in [`AI_CHAT_LOGS.md`](AI_CHAT_LOGS.md).

* **Tool:** Claude (Anthropic), in the Claude desktop app
* **What it did:** helped explain A*, BFS, Dijkstra, and heuristic admissibility; helped write and organize the code in `pathfinding/`, `visualizer.py`, `window.py`, `main.py`, `benchmark.py`, and the tests; redesigned the visualizer's look and fixed its blurriness on Retina screens; added code comments; helped draft this README
* **What I did:** read through all of the pathfinding algorithms in the project (BFS, Dijkstra, Greedy Best First, and A*) and found A* to be the best of them for finding the cheapest path. I already knew Dijkstra's algorithm from my data structures class; this project taught me more about heuristics and where the other pathfinding algorithms came from
* **Why:** to learn how A* works by building a complete, testable version and then experimenting with it
* Each source file also has an AI use note in its header comment
* **Chat logs:** the full conversations with Claude are in [`AI_CHAT_LOGS.md`](AI_CHAT_LOGS.md), word for word, with a table of what each chat covered

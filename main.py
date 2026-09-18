"""
main.py
Entry point for Project 1: A* Pathfinding Exploration (ADV Machine Learning and AI).

Run:  python main.py

This just opens the interactive visualizer. The rest of the project:
    visualizer.py              the PyGame UI (controls are listed at its top)
    pathfinding/search.py      A*, Dijkstra, BFS, and Greedy Best First
    pathfinding/heuristics.py  the heuristic functions
    benchmark.py               the heuristic experiment (python benchmark.py)
    tests/                     correctness and edge case tests (python -m pytest)

See README.md for how everything works and what the experiment found.

AI use: this project is being developed through chats with Claude (Anthropic).
See "AI Use" in README.md. Saved chat logs showing how we worked: AI_CHAT_LOGS.md.
"""

from visualizer import App


if __name__ == "__main__":
    App().run()

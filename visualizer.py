"""
visualizer.py
Interactive PyGame visualizer for A*, Dijkstra, BFS, and Greedy Best First.

Run:  python visualizer.py

Controls (also shown on screen):
    Left drag        draw walls
    Shift + drag     paint mud (costs 5 to cross)
    Right drag       erase
    S / E            move Start / End to the mouse
    SPACE            run or pause the search
    N                advance one step
    R                reset the search (keep the map)
    C                clear the map
    G / M            random map / maze
    A                cycle algorithm
    H                cycle heuristic
    D                toggle diagonal movement
    [ / ]            heuristic weight down / up
    - / =            animation speed down / up
    TAB              compare every algorithm on this map
    ESC              quit

AI use: written with help from Claude (Anthropic). See "AI Use" in README.md.
"""

import sys

import pygame

from pathfinding.grid import Grid
from pathfinding.heuristics import HEURISTICS
from pathfinding.search import ALGORITHMS, run_search, search_steps

# layout
COLS, ROWS = 40, 33
CELL = 22
PANEL_W = 340
GRID_W, GRID_H = COLS * CELL, ROWS * CELL
WIN_W, WIN_H = GRID_W + PANEL_W, GRID_H

# colors
BG = (246, 246, 242)
GRID_LINE = (222, 222, 216)
WALL = (40, 44, 52)
MUD = (165, 124, 82)
CLOSED = (170, 196, 235)
FRONTIER = (160, 225, 170)
CURRENT = (255, 150, 60)
PATH = (250, 205, 40)
START = (40, 160, 80)
GOAL = (215, 55, 60)
PANEL_BG = (30, 33, 40)
TEXT = (232, 232, 232)
MUTED = (150, 156, 168)
ACCENT = (250, 205, 40)

SPEEDS = [1, 2, 5, 10, 25, 60, 200]   # expansions per frame
WEIGHTS = [1.0, 1.2, 1.5, 2.0, 3.0, 5.0]


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("A* Pathfinding Explorer")
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("menlo,consolas,dejavusansmono,monospace", 14)
        self.big = pygame.font.SysFont("menlo,consolas,dejavusansmono,monospace", 18, bold=True)

        self.grid = Grid(COLS, ROWS, allow_diagonal=False)
        self.start = (3, ROWS // 2)
        self.goal = (COLS - 4, ROWS // 2)

        self.algo_i = 0
        self.heur_names = list(HEURISTICS)
        self.heur_i = 0
        self.weight_i = 0
        self.speed_i = 3

        self.comparison = []   # rows for the TAB comparison table
        self.reset_search()

    # state helpers

    @property
    def algorithm(self):
        return ALGORITHMS[self.algo_i]

    @property
    def heuristic_name(self):
        return self.heur_names[self.heur_i]

    @property
    def weight(self):
        return WEIGHTS[self.weight_i]

    def reset_search(self):
        """Throw away any search in progress; keep the map."""
        self.gen = None
        self.running = False
        self.step = None
        self.result = None

    def begin_search(self):
        self.gen = search_steps(self.grid, self.start, self.goal, self.algorithm,
                                HEURISTICS[self.heuristic_name], self.weight)
        self.step = None
        self.result = None

    def advance(self, n):
        """Expand up to n cells. Stops when the generator finishes."""
        if self.gen is None:
            if self.result is not None:
                return
            self.begin_search()
        for _ in range(n):
            try:
                self.step = next(self.gen)
            except StopIteration as done:
                self.result = done.value
                self.gen = None
                self.running = False
                return

    def compare_all(self):
        """Run every algorithm (and A* with every heuristic) instantly on this map."""
        rows = []
        configs = [("BFS", "Zero (Dijkstra)"), ("Dijkstra", "Zero (Dijkstra)"),
                   ("Greedy", self.heuristic_name)]
        configs += [("A*", name) for name in self.heur_names if name != "Zero (Dijkstra)"]
        for algo, hname in configs:
            r = run_search(self.grid, self.start, self.goal, algo, HEURISTICS[hname], self.weight)
            label = algo if algo in ("BFS", "Dijkstra") else f"{algo} {hname}"
            rows.append((label, r))
        self.comparison = rows

    # input

    def cell_at(self, pos):
        x, y = pos
        if 0 <= x < GRID_W and 0 <= y < GRID_H:
            return (x // CELL, y // CELL)
        return None

    def handle_mouse(self):
        buttons = pygame.mouse.get_pressed()
        cell = self.cell_at(pygame.mouse.get_pos())
        if cell is None or cell in (self.start, self.goal):
            return
        shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
        changed = False
        if buttons[0]:
            if shift:
                self.grid.set_mud(cell)
            else:
                self.grid.set_wall(cell)
            changed = True
        elif buttons[2]:
            self.grid.clear_cell(cell)
            changed = True
        if changed:
            self.reset_search()
            self.comparison = []

    def handle_key(self, key):
        mouse_cell = self.cell_at(pygame.mouse.get_pos())
        map_changed = False

        if key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()
        elif key == pygame.K_SPACE:
            if self.result is not None:
                self.reset_search()
            self.running = not self.running
        elif key == pygame.K_n:
            self.running = False
            self.advance(1)
        elif key == pygame.K_r:
            self.reset_search()
        elif key == pygame.K_c:
            self.grid.clear()
            map_changed = True
        elif key == pygame.K_g:
            self.grid.randomize(keep_clear=[self.start, self.goal])
            map_changed = True
        elif key == pygame.K_m:
            self.grid.carve_maze(keep_clear=[self.start, self.goal])
            map_changed = True
        elif key == pygame.K_a:
            self.algo_i = (self.algo_i + 1) % len(ALGORITHMS)
            self.reset_search()
        elif key == pygame.K_h:
            self.heur_i = (self.heur_i + 1) % len(self.heur_names)
            self.reset_search()
        elif key == pygame.K_d:
            self.grid.allow_diagonal = not self.grid.allow_diagonal
            map_changed = True
        elif key == pygame.K_LEFTBRACKET:
            self.weight_i = max(0, self.weight_i - 1)
            self.reset_search()
        elif key == pygame.K_RIGHTBRACKET:
            self.weight_i = min(len(WEIGHTS) - 1, self.weight_i + 1)
            self.reset_search()
        elif key == pygame.K_MINUS:
            self.speed_i = max(0, self.speed_i - 1)
        elif key in (pygame.K_EQUALS, pygame.K_PLUS):
            self.speed_i = min(len(SPEEDS) - 1, self.speed_i + 1)
        elif key == pygame.K_TAB:
            self.compare_all()
        elif key == pygame.K_s and mouse_cell and mouse_cell != self.goal:
            self.grid.clear_cell(mouse_cell)
            self.start = mouse_cell
            map_changed = True
        elif key == pygame.K_e and mouse_cell and mouse_cell != self.start:
            self.grid.clear_cell(mouse_cell)
            self.goal = mouse_cell
            map_changed = True

        if map_changed:
            self.reset_search()
            self.comparison = []

    # drawing

    def fill_cell(self, cell, color, inset=0):
        x, y = cell
        pygame.draw.rect(self.screen, color,
                         (x * CELL + inset, y * CELL + inset, CELL - 2 * inset, CELL - 2 * inset))

    def draw_grid(self):
        self.screen.fill(BG, (0, 0, GRID_W, GRID_H))

        # search state underneath
        if self.result is not None:
            closed, frontier, current = self.result.closed, self.result.frontier, None
        elif self.step is not None:
            closed, frontier, current = self.step.closed, self.step.frontier, self.step.current
        else:
            closed, frontier, current = (), (), None
        for c in closed:
            self.fill_cell(c, CLOSED)
        for c in frontier:
            self.fill_cell(c, FRONTIER)

        # terrain on top (mud stays visible, but tinted cells show under it via inset)
        for c in self.grid.mud:
            inset = 4 if (c in closed or c in frontier) else 0
            self.fill_cell(c, MUD, inset)
        for c in self.grid.walls:
            self.fill_cell(c, WALL)

        if current is not None:
            self.fill_cell(current, CURRENT)

        # final path as a thick line through cell centers
        if self.result is not None and self.result.found and len(self.result.path) > 1:
            pts = [(x * CELL + CELL // 2, y * CELL + CELL // 2) for x, y in self.result.path]
            pygame.draw.lines(self.screen, PATH, False, pts, 6)

        for x in range(COLS + 1):
            pygame.draw.line(self.screen, GRID_LINE, (x * CELL, 0), (x * CELL, GRID_H))
        for y in range(ROWS + 1):
            pygame.draw.line(self.screen, GRID_LINE, (0, y * CELL), (GRID_W, y * CELL))

        self.fill_cell(self.start, START, 2)
        self.fill_cell(self.goal, GOAL, 2)

    def text(self, s, x, y, color=TEXT, font=None):
        surf = (font or self.font).render(s, True, color)
        self.screen.blit(surf, (x, y))
        return y + surf.get_height() + 3

    def draw_panel(self):
        x0 = GRID_W
        self.screen.fill(PANEL_BG, (x0, 0, PANEL_W, WIN_H))
        x = x0 + 16
        y = self.text("A* Pathfinding Explorer", x, 14, ACCENT, self.big) + 8

        uses_h = self.algorithm in ("A*", "Greedy")
        y = self.text(f"Algorithm   {self.algorithm}", x, y)
        y = self.text(f"Heuristic   {self.heuristic_name if uses_h else '(not used)'}", x, y,
                      TEXT if uses_h else MUTED)
        y = self.text(f"Weight      {self.weight:g}" if self.algorithm == "A*" else "Weight      (A* only)",
                      x, y, TEXT if self.algorithm == "A*" else MUTED)
        y = self.text(f"Movement    {'8 way (diagonal)' if self.grid.allow_diagonal else '4 way'}", x, y)
        y = self.text(f"Speed       {SPEEDS[self.speed_i]} cells/frame", x, y)
        if self.algorithm == "A*":
            y = self.text("priority f = g + w*h", x, y, MUTED)
        elif self.algorithm == "Dijkstra":
            y = self.text("priority = g (cost so far)", x, y, MUTED)
        elif self.algorithm == "BFS":
            y = self.text("priority = steps (ignores cost)", x, y, MUTED)
        else:
            y = self.text("priority = h (ignores cost)", x, y, MUTED)
        y += 10

        # live stats
        y = self.text("Stats", x, y, ACCENT, self.big)
        if self.result is not None:
            r = self.result
            status = "path found" if r.found else "NO PATH"
            y = self.text(f"Status      {status}", x, y, TEXT if r.found else GOAL)
            y = self.text(f"Expanded    {r.expanded}", x, y)
            y = self.text(f"Max open    {r.max_frontier}", x, y)
            if r.found:
                y = self.text(f"Path cost   {r.cost:.2f}", x, y)
                y = self.text(f"Path cells  {len(r.path)}", x, y)
            y = self.text(f"Time        {r.elapsed_ms:.1f} ms (animated)", x, y, MUTED)
        elif self.step is not None:
            y = self.text("Status      searching...", x, y)
            y = self.text(f"Expanded    {len(self.step.closed)}", x, y)
            y = self.text(f"Open        {len(self.step.frontier)}", x, y)
        else:
            y = self.text("Press SPACE to start", x, y, MUTED)
        y += 10

        # comparison table
        if self.comparison:
            y = self.text("Compare (TAB)", x, y, ACCENT, self.big)
            y = self.text(f"{'method':<21}{'exp':>5}{'cost':>8}", x, y, MUTED)
            best = min((r.cost for _, r in self.comparison if r.found), default=None)
            for label, r in self.comparison:
                cost = f"{r.cost:.1f}" if r.found else "none"
                opt = r.found and best is not None and abs(r.cost - best) < 1e-9
                color = TEXT if opt else (240, 130, 110)
                y = self.text(f"{label[:21]:<21}{r.expanded:>5}{cost:>8}", x, y, color)
            y = self.text("red = not the cheapest path", x, y, MUTED)
            y += 6

        # legend (two columns) + controls pinned to the bottom
        items = [(START, "start"), (GOAL, "goal"), (WALL, "wall"), (MUD, "mud (cost 5)"),
                 (FRONTIER, "open"), (CLOSED, "explored"), (PATH, "final path"),
                 (CURRENT, "current")]
        top = WIN_H - 100 - 4 * 19
        for i, (color, label) in enumerate(items):
            lx = x + (i % 2) * 150
            ly = top + (i // 2) * 19
            pygame.draw.rect(self.screen, color, (lx, ly + 3, 12, 12))
            self.text(label, lx + 20, ly, MUTED)
        keys = ["drag wall   shift mud   right erase",
                "S/E move start/end   SPACE run  N step",
                "A algo  H heur  D diag  [ ] weight",
                "G random  M maze  C clear  R reset",
                "- = speed   TAB compare   ESC quit"]
        yk = WIN_H - 96
        for k in keys:
            yk = self.text(k, x, yk, MUTED)

    # main loop

    def run(self, max_frames=None):
        frames = 0
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                if event.type == pygame.KEYDOWN:
                    self.handle_key(event.key)
            self.handle_mouse()

            if self.running:
                self.advance(SPEEDS[self.speed_i])

            self.draw_grid()
            self.draw_panel()
            pygame.display.flip()
            self.clock.tick(60)

            frames += 1
            if max_frames and frames >= max_frames:
                return


if __name__ == "__main__":
    App().run()

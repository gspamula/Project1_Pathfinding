"""
visualizer.py
Interactive PyGame visualizer for A*, Dijkstra, BFS, and Greedy Best First.

Run:  python visualizer.py   (or python main.py)

Controls (also shown in the window):
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

Layout: the map is on the left. The side panel shows the settings, a plain
English explanation of the current algorithm and heuristic, live search
stats, and the TAB comparison table. The bar under the map holds the color
legend and the controls.

All drawing coordinates are in screen "points". On a Retina screen the
canvas has 2 pixels per point (see window.py), so every draw call goes
through a few small helpers (rect, circle, text) that multiply by the scale.
That keeps the drawing code readable and the picture sharp.

AI use: this project is being developed through chats with Claude (Anthropic).
See "AI Use" in README.md. Saved chat logs showing how we worked: AI_CHAT_LOGS.md.
"""

import pygame
import pygame.gfxdraw

from pathfinding.grid import Grid, MUD_COST
from pathfinding.heuristics import HEURISTICS
from pathfinding.search import ALGORITHMS, run_search, search_steps
from window import Window, usable_screen_size

# layout, in points
COLS, ROWS = 40, 33          # same map size as the benchmark
MAX_CELL, MIN_CELL = 22, 12  # the cell size shrinks to fit smaller screens
PANEL_W = 330                # side panel width
PANEL_MIN_H = 650            # the panel needs this much height at most
PAD = 18                     # inner margin of the panel
BAR_PAD, BAR_ROW_H = 9, 22   # bottom bar margin and row height

FONT_NAMES = "helveticaneue,segoeui,arial"

# map colors (light)
MAP_BG = (250, 250, 248)
GRID_LINE = (233, 233, 229)
WALL = (55, 62, 77)
MUD = (163, 121, 80)
EXPLORED_EARLY = (218, 232, 251)   # explored cells shade from light (expanded early)
EXPLORED_LATE = (137, 177, 235)    # ... to darker (expanded late)
FRONTIER = (150, 221, 172)
CURRENT = (255, 138, 61)
PATH = (255, 193, 45)
PATH_EDGE = (196, 128, 0)
START = (32, 168, 96)
GOAL = (230, 70, 80)

# panel colors (dark)
CHROME = (23, 26, 33)
CARD = (34, 38, 47)
TEXT = (237, 239, 244)
MUTED = (143, 151, 166)
FAINT = (98, 106, 121)
ACCENT = (255, 193, 45)
GOOD = (96, 205, 140)
BAD = (242, 116, 104)
KEY_BG = (50, 56, 68)
KEY_TEXT = (226, 230, 238)
BAR_FILL = (120, 163, 228)

SPEEDS = [1, 2, 5, 10, 25, 60, 200]   # expansions per frame
WEIGHTS = [1.0, 1.2, 1.5, 2.0, 3.0, 5.0]  # heuristic weight w in f = g + w*h (1 = normal A*)

ALGORITHM_NAMES = {"A*": "A*", "Dijkstra": "Dijkstra", "BFS": "Breadth first", "Greedy": "Greedy best first"}

# Plain English explanations shown in the panel.
ALGORITHM_INFO = {
    "A*": "A* explores the cell with the lowest cost so far plus estimated cost left, "
          "so it heads toward the goal.",
    "Dijkstra": "Dijkstra explores the cheapest cell found so far. It always finds the "
                "cheapest path, but spreads out in every direction.",
    "BFS": "Breadth first search explores cells in order of how many moves away they are. "
           "It finds the fewest moves but ignores that mud costs more.",
    "Greedy": "Greedy best first explores whatever looks closest to the goal. It is very "
              "fast, but ignores the cost so far, so its paths are often expensive.",
}

# Legend and controls in the bottom bar.
LEGEND = [("start", "Start"), ("goal", "Goal"), ("wall", "Wall"), ("mud", f"Mud (costs {MUD_COST})"),
          ("frontier", "Frontier"), ("explored", "Explored (early to late)"),
          ("current", "Current"), ("path", "Final path")]
CONTROLS = [(["Space"], "Run / pause"), (["N"], "Step"), (["R"], "Reset"), (["Tab"], "Compare all"),
            (["G"], "Random map"), (["M"], "Maze"), (["C"], "Clear"), (["S", "E"], "Move start / end"),
            (["Drag"], "Wall"), (["Shift + drag"], "Mud"), (["Right drag"], "Erase"), (["Esc"], "Quit")]


def heuristic_note(name, diagonal):
    """One sentence on how well a heuristic fits the current movement rules, and whether it is a warning."""
    if name == "Manhattan":
        if diagonal:
            return "Manhattan overestimates diagonal moves, so the path may not be the cheapest.", True
        return "Manhattan is the exact open ground distance for 4 direction moves: the best fit here.", False
    if name == "Octile":
        if diagonal:
            return "Octile is the exact open ground distance with diagonal moves: the best fit here.", False
        return "Octile never overestimates, but Manhattan is a closer guess for 4 direction moves.", False
    if name == "Euclidean":
        return "Euclidean (straight line) never overestimates, but it guesses low, so more cells get explored.", False
    if name == "Chebyshev":
        return "Chebyshev never overestimates, but it is the lowest guess, so the most cells get explored.", False
    if name == "Octile + tiebreak":
        return "Octile plus a tiny nudge toward the straight start to goal line, so ties go to cells on it.", False
    return "A zero estimate gives A* no sense of direction, so it behaves exactly like Dijkstra.", False


def mix(a, b, t):
    """Blend two colors: t = 0 gives a, t = 1 gives b."""
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


class App:
    """The whole visualizer: owns the grid, the running search, and the window.

    The search itself lives in pathfinding/search.py as a generator. The app
    only pulls steps out of it (a few per frame) and draws whatever state the
    latest step reports, so the algorithm code knows nothing about PyGame.
    """

    def __init__(self, offscreen_scale=None):
        """Open the window and start on an empty 4 way grid with A* selected.

        offscreen_scale draws to an off screen canvas instead of a window
        (used to save the README screenshot at Retina resolution).
        """
        pygame.init()
        self.grid = Grid(COLS, ROWS, allow_diagonal=False)
        self.start = (3, ROWS // 2)
        self.goal = (COLS - 4, ROWS // 2)

        # The current settings are stored as indexes into their option lists,
        # so the A / H / [ ] / - = keys can simply cycle through them.
        self.algo_i = 0
        self.heur_names = list(HEURISTICS)
        self.heur_i = 0
        self.weight_i = 0
        self.speed_i = 3

        self.comparison = []   # rows for the TAB comparison table
        self.quit = False

        # Measure text at scale 1 to plan the layout, open a window that fits
        # the screen, then reload the fonts at the window's real resolution.
        self.scale = 1
        self.load_fonts()
        self.plan_layout(fit_screen=offscreen_scale is None)
        self.window = Window("A* Pathfinding Explorer", (self.win_w, self.win_h), offscreen_scale)
        self.canvas = self.window.canvas
        self.scale = self.window.scale
        self.load_fonts()
        self.clock = pygame.time.Clock()
        self.reset_search()

    # layout

    def load_fonts(self):
        """Create the fonts at the canvas resolution (so text is sharp on Retina screens)."""
        def font(size, bold=False):
            return pygame.font.SysFont(FONT_NAMES, round(size * self.scale), bold=bold)
        self.f_title = font(19, bold=True)
        self.f_body = font(13)
        self.f_small = font(11.5)
        self.f_label = font(10.5, bold=True)
        self.f_stat = font(17, bold=True)
        self.f_key = font(10.5, bold=True)

    def plan_layout(self, fit_screen):
        """Pick the cell size and work out where everything goes, all in points.

        The cell size is the largest (up to MAX_CELL) that lets the whole
        window fit on the screen, so it works on small laptop screens too.
        """
        avail = usable_screen_size() if fit_screen else None
        for cell in range(MAX_CELL, MIN_CELL - 1, -1):
            self.cell = cell
            self.grid_w, self.grid_h = COLS * cell, ROWS * cell
            bar_h = self.flow_bar()
            self.win_w = self.grid_w + PANEL_W
            self.win_h = max(self.grid_h + bar_h, PANEL_MIN_H)
            if avail is None or (self.win_w <= avail[0] and self.win_h <= avail[1]):
                break
        self.bar_h = self.win_h - self.grid_h

    def flow_bar(self):
        """Flow the legend, then the controls, into rows as wide as the map. Returns the bar height."""
        self.bar_items = []    # (x, row, kind, data)
        row, x = 0, BAR_PAD
        for group in (LEGEND, CONTROLS):
            for item in group:
                kind = "legend" if group is LEGEND else "control"
                w = self.bar_item_width(kind, item)
                if x + w > self.grid_w - BAR_PAD and x > BAR_PAD:
                    row, x = row + 1, BAR_PAD
                self.bar_items.append((x, row, kind, item))
                x += w + 18
            row, x = row + 1, BAR_PAD
        return 2 * BAR_PAD + row * BAR_ROW_H

    def bar_item_width(self, kind, item):
        """Width of one legend entry or control hint in the bottom bar."""
        if kind == "legend":
            return 14 + 6 + self.text_width(item[1], self.f_small)
        keys, label = item
        return sum(self.key_width(k) + 4 for k in keys) + 3 + self.text_width(label, self.f_small)

    # drawing helpers (all take points and convert to canvas pixels)

    def px(self, v):
        return round(v * self.scale)

    def to_rect(self, x, y, w, h):
        return pygame.Rect(self.px(x), self.px(y), self.px(x + w) - self.px(x), self.px(y + h) - self.px(y))

    def rect(self, color, x, y, w, h, radius=0):
        pygame.draw.rect(self.canvas, color, self.to_rect(x, y, w, h), border_radius=self.px(radius))

    def circle(self, color, x, y, r):
        """A smooth (anti aliased) filled circle."""
        cx, cy, pr = self.px(x), self.px(y), self.px(r)
        pygame.gfxdraw.aacircle(self.canvas, cx, cy, pr, color)
        pygame.gfxdraw.filled_circle(self.canvas, cx, cy, pr, color)

    def text(self, s, x, y, font, color, align="left"):
        """Draw text with its top at y. align is "left", "right" or "center" around x. Returns the width."""
        surf = font.render(s, True, color)
        w = surf.get_width() / self.scale
        if align == "right":
            x -= w
        elif align == "center":
            x -= w / 2
        self.canvas.blit(surf, (self.px(x), self.px(y)))
        return w

    def text_width(self, s, font):
        return font.size(s)[0] / self.scale

    def text_height(self, font):
        return font.get_height() / self.scale

    def wrap(self, s, font, width):
        """Split text into lines that fit in width points."""
        lines, line = [], ""
        for word in s.split():
            trial = f"{line} {word}".strip()
            if line and self.text_width(trial, font) > width:
                lines.append(line)
                line = word
            else:
                line = trial
        return lines + [line] if line else lines

    def key_width(self, label):
        return self.text_width(label, self.f_key) + 12

    def key(self, label, x, y):
        """Draw a keyboard key "cap" with its left edge at x, centered on y. Returns its width."""
        w, h = self.key_width(label), 18
        self.rect(KEY_BG, x, y - h / 2, w, h, radius=4)
        self.text(label, x + w / 2, y - self.text_height(self.f_key) / 2, self.f_key, KEY_TEXT, "center")
        return w

    # state helpers

    @property
    def algorithm(self):
        """Name of the selected algorithm ("A*", "Dijkstra", "BFS" or "Greedy")."""
        return ALGORITHMS[self.algo_i]

    @property
    def heuristic_name(self):
        """Key of the selected heuristic in HEURISTICS."""
        return self.heur_names[self.heur_i]

    @property
    def weight(self):
        """Selected heuristic weight w (only A* uses it)."""
        return WEIGHTS[self.weight_i]

    def reset_search(self):
        """Throw away any search in progress; keep the map.

        The search always has exactly one of three states:
            gen is None and result is None      -> nothing started yet
            gen is a generator                  -> search in progress
            gen is None and result is not None  -> search finished
        """
        self.gen = None
        self.running = False
        self.step = None      # latest SearchStep, used to draw the search in progress
        self.result = None    # SearchResult, set once the generator finishes
        self.order = {}       # cell -> when it was expanded (0, 1, 2, ...), for shading

    def begin_search(self):
        """Create a fresh search generator using the current settings."""
        self.gen = search_steps(self.grid, self.start, self.goal, self.algorithm,
                                HEURISTICS[self.heuristic_name], self.weight)
        self.step = None
        self.result = None
        self.order = {}

    def advance(self, n):
        """Expand up to n cells. Stops when the generator finishes.

        Each next() call runs the search loop until it expands one more cell.
        When the search ends, the generator raises StopIteration and the
        SearchResult it returned is stored in done.value.
        """
        if self.gen is None:
            if self.result is not None:
                return   # already finished; R or SPACE starts a new search
            self.begin_search()
        for _ in range(n):
            try:
                self.step = next(self.gen)
                self.order[self.step.current] = len(self.order)
            except StopIteration as done:
                self.result = done.value
                self.gen = None
                self.running = False
                return

    def compare_all(self):
        """Run every algorithm (and A* with every heuristic) instantly on this map.

        This uses run_search (no animation), so the whole table is ready in a
        few milliseconds. The selected weight is applied to every A* row, so
        pressing ] and then TAB shows weighted A* against the exact methods.
        """
        rows = []
        configs = [("BFS", "Zero (Dijkstra)"), ("Dijkstra", "Zero (Dijkstra)"),
                   ("Greedy", self.heuristic_name)]
        configs += [("A*", name) for name in self.heur_names if name != "Zero (Dijkstra)"]
        for algo, hname in configs:
            r = run_search(self.grid, self.start, self.goal, algo, HEURISTICS[hname], self.weight)
            label = algo if algo in ("BFS", "Dijkstra") else f"{algo} {hname}"
            rows.append((label, algo, hname, r))
        self.comparison = rows

    # input

    def cell_at(self, pos):
        """Convert a mouse position (in points) to a grid cell, or None if it is off the map."""
        x, y = pos
        if 0 <= x < self.grid_w and 0 <= y < self.grid_h:
            return (int(x // self.cell), int(y // self.cell))
        return None

    def handle_mouse(self):
        """Paint walls, mud, or empty ground under the mouse while a button is held.

        This reads the current button state every frame (instead of waiting
        for click events), which is what makes click and drag drawing work.
        """
        buttons = pygame.mouse.get_pressed()
        cell = self.cell_at(pygame.mouse.get_pos())
        # Never paint over the start or goal, or they could become walls.
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
        # An old search (or comparison table) would describe a map that no
        # longer exists, so editing the map throws them away.
        if changed:
            self.reset_search()
            self.comparison = []

    def handle_key(self, key):
        """Handle one key press (see the controls list at the top of this file)."""
        mouse_cell = self.cell_at(pygame.mouse.get_pos())
        map_changed = False

        if key == pygame.K_ESCAPE:
            self.quit = True
        elif key == pygame.K_SPACE:
            # If the last search already finished, SPACE starts a new one.
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
            # Changing the movement rules changes the costs, so treat it like a map edit.
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
        # Moving start/end clears the cell first so the endpoint is never a wall.
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

    # drawing: map

    def fill_cell(self, cell, color, inset=0, radius=0):
        """Fill one cell. inset > 0 leaves a border of whatever is underneath."""
        x, y = cell
        c = self.cell
        self.rect(color, x * c + inset, y * c + inset, c - 2 * inset, c - 2 * inset, radius)

    def search_state(self):
        """(closed, frontier, current) for the finished search, the search in progress, or nothing."""
        if self.result is not None:
            return self.result.closed, self.result.frontier, None
        if self.step is not None:
            return self.step.closed, self.step.frontier, self.step.current
        return (), (), None

    def draw_map(self):
        """Draw the map and the search state, back to front.

        Order matters because later layers cover earlier ones: explored and
        open cells, grid lines, terrain, the cell being expanded, the final
        path, and finally the start and goal markers on top.
        """
        c = self.cell
        self.rect(MAP_BG, 0, 0, self.grid_w, self.grid_h)

        # Explored cells shade from light (expanded early) to darker (expanded
        # late), so you can watch the search spread out from the start.
        closed, frontier, current = self.search_state()
        latest = max(1, len(self.order))
        for cell in closed:
            self.fill_cell(cell, mix(EXPLORED_EARLY, EXPLORED_LATE, self.order.get(cell, latest) / latest))
        for cell in frontier:
            self.fill_cell(cell, FRONTIER, inset=1, radius=3)

        line_w = 1 / self.scale   # one real pixel
        for x in range(COLS + 1):
            self.rect(GRID_LINE, x * c, 0, line_w, self.grid_h)
        for y in range(ROWS + 1):
            self.rect(GRID_LINE, 0, y * c, self.grid_w, line_w)

        # Mud is inset further on searched cells so the search color shows around it.
        for cell in self.grid.mud:
            searched = cell in closed or cell in frontier
            self.fill_cell(cell, MUD, inset=c * (0.2 if searched else 0.08), radius=3)
        for cell in self.grid.walls:
            self.fill_cell(cell, WALL)

        if current is not None:
            self.fill_cell(current, CURRENT, inset=1, radius=3)

        # Final path: a thick line through the cell centers with a darker edge.
        # The circles at each point round off the corners; they are sized in
        # whole pixels to match the line exactly, so they don't stick out.
        if self.result is not None and self.result.found and len(self.result.path) > 1:
            pts = [(self.px(x * c + c / 2), self.px(y * c + c / 2)) for x, y in self.result.path]
            for color, width in ((PATH_EDGE, c * 0.36), (PATH, c * 0.24)):
                r = max(1, self.px(width) // 2)
                pygame.draw.lines(self.canvas, color, False, pts, 2 * r)
                for p in pts:
                    pygame.draw.circle(self.canvas, color, p, r)

        for cell, color in ((self.start, START), (self.goal, GOAL)):
            x, y = cell
            self.circle((255, 255, 255), x * c + c / 2, y * c + c / 2, c * 0.46)
            self.circle(color, x * c + c / 2, y * c + c / 2, c * 0.36)

    # drawing: bottom bar

    def draw_legend_swatch(self, kind, x, y):
        """Draw the small sample for one legend entry, 14 points wide, centered on y."""
        s = 14
        top = y - s / 2
        if kind in ("start", "goal"):
            self.circle(START if kind == "start" else GOAL, x + s / 2, y, s / 2 - 1)
        elif kind == "wall":
            self.rect(WALL, x, top, s, s, radius=2)
        elif kind == "mud":
            self.rect(MUD, x, top, s, s, radius=3)
        elif kind == "frontier":
            self.rect(FRONTIER, x, top, s, s, radius=3)
        elif kind == "explored":
            self.rect(EXPLORED_EARLY, x, top, s / 2, s)
            self.rect(EXPLORED_LATE, x + s / 2, top, s / 2, s)
        elif kind == "current":
            self.rect(CURRENT, x, top, s, s, radius=3)
        elif kind == "path":
            self.rect(PATH_EDGE, x - 1, y - 3.5, s + 2, 7, radius=3)
            self.rect(PATH, x, y - 2.5, s, 5, radius=2)

    def draw_bar(self):
        """Draw the legend and the controls under the map."""
        self.rect(CHROME, 0, self.grid_h, self.grid_w, self.bar_h)
        for x, row, kind, item in self.bar_items:
            y = self.grid_h + BAR_PAD + row * BAR_ROW_H + BAR_ROW_H / 2
            text_top = y - self.text_height(self.f_small) / 2
            if kind == "legend":
                self.draw_legend_swatch(item[0], x, y)
                self.text(item[1], x + 20, text_top, self.f_small, MUTED)
            else:
                keys, label = item
                for k in keys:
                    x += self.key(k, x, y) + 4
                self.text(label, x + 3, text_top, self.f_small, MUTED)

    # drawing: side panel

    def section(self, title, x, y):
        """Draw a small, letter spaced section heading and return the y below it."""
        for ch in title.upper():
            x += self.text(ch, x, y, self.f_label, FAINT) + 1.2
        return y + 20

    def draw_settings(self, x, y, w):
        """Settings rows (label, value, and the keys that change it) and the explanation card."""
        uses_h = self.algorithm in ("A*", "Greedy")
        is_astar = self.algorithm == "A*"
        rows = [
            ("Algorithm", ALGORITHM_NAMES[self.algorithm], True, ["A"]),
            ("Heuristic", self.heuristic_name if uses_h else "Not used", uses_h, ["H"]),
            ("Weight", (f"{self.weight:g}×" + (" (normal)" if self.weight == 1 else " (faster)"))
             if is_astar else "A* only", is_astar, ["[", "]"]),
            ("Movement", "8 directions" if self.grid.allow_diagonal else "4 directions", True, ["D"]),
            ("Speed", f"{SPEEDS[self.speed_i]} cells per frame", True, ["−", "="]),
        ]
        body_h = self.text_height(self.f_body)
        for label, value, active, keys in rows:
            mid = y + 11
            self.text(label, x, mid - body_h / 2, self.f_body, MUTED)
            self.text(value, x + 84, mid - body_h / 2, self.f_body, TEXT if active else FAINT)
            kx = x + w
            for k in reversed(keys):
                kx -= self.key_width(k)
                self.key(k, kx, mid)
                kx -= 4
            y += 24

        # Explanation card: what the algorithm does, and for A* how the
        # heuristic and weight affect it. Warnings are drawn in red.
        notes = [(ALGORITHM_INFO[self.algorithm], MUTED)]
        if is_astar:
            note, warn = heuristic_note(self.heuristic_name, self.grid.allow_diagonal)
            notes.append((note, BAD if warn else TEXT))
            if self.weight > 1:
                notes.append((f"Weight {self.weight:g}× trusts the estimate more: fewer cells "
                              "explored, but the path may cost more.", ACCENT))
        line_h = self.text_height(self.f_small) + 2
        lines = []
        for i, (note, color) in enumerate(notes):
            if i:
                lines.append(("", None))   # small gap between notes
            lines += [(s, color) for s in self.wrap(note, self.f_small, w - 24)]
        card_h = 20 + sum(line_h if color else 5 for _, color in lines)
        y += 6
        self.rect(CARD, x, y, w, card_h, radius=8)
        ty = y + 10
        for s, color in lines:
            if color:
                self.text(s, x + 12, ty, self.f_small, color)
            ty += line_h if color else 5
        return y + card_h

    def draw_stats(self, x, y, w):
        """Status and four stat tiles for the current search."""
        r = self.result
        if r is not None:
            status, color = ("Path found", GOOD) if r.found else ("No path", BAD)
            explored, frontier = r.expanded, len(r.frontier)
            cost = f"{r.cost:.1f}" if r.found else "—"
            moves = f"{len(r.path) - 1}" if r.found else "—"
        else:
            if self.step is not None:
                status, color = ("Searching", ACCENT) if self.running else ("Paused", MUTED)
                explored, frontier = len(self.step.closed), len(self.step.frontier)
            else:
                status, color = ("Press Space to start", MUTED)
                explored = frontier = 0
            cost = moves = "—"

        self.section("Search", x, y)
        label_h = self.text_height(self.f_label)
        sw = self.text_width(status, self.f_small)
        self.circle(color, x + w - sw - 9, y + label_h / 2, 3.5)
        self.text(status, x + w, y + label_h / 2 - self.text_height(self.f_small) / 2, self.f_small, color, "right")
        y += 20

        tiles = [(f"{explored:,}", "explored"), (f"{frontier:,}", "frontier"), (cost, "path cost"), (moves, "moves")]
        gap = 6
        tw = (w - gap * 3) / 4
        for i, (value, label) in enumerate(tiles):
            tx = x + i * (tw + gap)
            self.rect(CARD, tx, y, tw, 46, radius=8)
            self.text(value, tx + 10, y + 6, self.f_stat, TEXT)
            self.text(label, tx + 10, y + 28, self.f_small, MUTED)
        return y + 46

    def draw_compare(self, x, y, w):
        """The TAB comparison table: cells explored as bars, and path cost (red = not the cheapest)."""
        self.section("Compare", x, y)
        self.key("Tab", x + w - self.key_width("Tab"), y + self.text_height(self.f_label) / 2)
        y += 22
        if not self.comparison:
            for line in self.wrap("Press Tab to run every method on this map at once and compare "
                                  "how many cells each explores and what its path costs.", self.f_small, w):
                self.text(line, x, y, self.f_small, FAINT)
                y += self.text_height(self.f_small) + 2
            return y

        bar_x, bar_w = x + 128, w - 128 - 86
        self.text("method", x, y, self.f_small, FAINT)
        self.text("cells explored", bar_x, y, self.f_small, FAINT)
        self.text("cost", x + w, y, self.f_small, FAINT, "right")
        y += 18
        most = max(r.expanded for *_, r in self.comparison) or 1
        best = min((r.cost for *_, r in self.comparison if r.found), default=None)
        small_h = self.text_height(self.f_small)
        for label, algo, hname, r in self.comparison:
            optimal = r.found and best is not None and abs(r.cost - best) < 1e-9
            selected = algo == self.algorithm and (algo in ("BFS", "Dijkstra") or hname == self.heuristic_name)
            mid = y + 9
            self.text(label, x, mid - small_h / 2, self.f_small, ACCENT if selected else TEXT)
            self.rect(BAR_FILL if optimal else BAD, bar_x, mid - 3.5, max(3, bar_w * r.expanded / most), 7,
                      radius=3)
            self.text(f"{r.expanded:,}", x + w - 44, mid - small_h / 2, self.f_small, MUTED, "right")
            self.text(f"{r.cost:.1f}" if r.found else "none", x + w, mid - small_h / 2, self.f_small,
                      TEXT if optimal else BAD, "right")
            y += 18
        note = "Red = not the cheapest path."
        if self.weight != 1:
            note += f" A* rows use weight {self.weight:g}×."
        for line in self.wrap(note, self.f_small, w):
            self.text(line, x, y + 4, self.f_small, FAINT)
            y += small_h + 2
        return y + 4

    def draw_panel(self):
        """Draw the side panel: title, settings, stats, and the comparison table."""
        x0 = self.grid_w
        self.rect(CHROME, x0, 0, PANEL_W, self.win_h)
        x, w = x0 + PAD, PANEL_W - 2 * PAD
        y = PAD
        self.text("A* Pathfinding Explorer", x, y, self.f_title, TEXT)
        y += 25
        self.text("Watch how a heuristic steers the search.", x, y, self.f_small, MUTED)
        y += 26
        y = self.draw_settings(x, self.section("Settings", x, y), w) + 20
        y = self.draw_stats(x, y, w) + 20
        return self.draw_compare(x, y, w)

    def draw(self):
        """Draw one complete frame onto the canvas."""
        self.draw_map()
        self.draw_bar()
        self.draw_panel()

    # main loop

    def run(self, max_frames=None):
        """Main loop at 60 frames per second: handle input, advance the search, redraw.

        max_frames stops the loop after that many frames, which is handy for
        checking that the window opens without errors.
        """
        frames = 0
        while not self.quit:
            for event in pygame.event.get():
                if event.type in (pygame.QUIT, pygame.WINDOWCLOSE):
                    self.quit = True
                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event.key)
            self.handle_mouse()

            if self.running:
                self.advance(SPEEDS[self.speed_i])

            self.draw()
            self.window.present()
            self.clock.tick(60)

            frames += 1
            if max_frames and frames >= max_frames:
                break
        self.window.close()
        pygame.quit()


if __name__ == "__main__":
    App().run()

"""
Project 1: A* Pathfinding Exploration Project
ADV Machine Learning and AI - Mr. Cochran

Starter scaffold only: sets up a Pygame window and an empty grid so you can
confirm your environment works before you build the A* algorithm yourself.

TODO (per the assignment):
  1. Represent the grid/graph you will search over.
  2. Implement A* from scratch (open/closed sets, g/h/f scores, backtracking
     the path).
  3. Try at least two different heuristics and compare their effect on
     performance and accuracy.
  4. Use Pygame to visualize the search happening step by step, plus the
     final path found.
"""

import pygame

WINDOW_WIDTH, WINDOW_HEIGHT = 800, 800
GRID_SIZE = 20  # 20x20 grid of cells
CELL_SIZE = WINDOW_WIDTH // GRID_SIZE

WHITE = (255, 255, 255)
GREY = (200, 200, 200)


def draw_grid(surface):
    for x in range(0, WINDOW_WIDTH, CELL_SIZE):
        pygame.draw.line(surface, GREY, (x, 0), (x, WINDOW_HEIGHT))
    for y in range(0, WINDOW_HEIGHT, CELL_SIZE):
        pygame.draw.line(surface, GREY, (0, y), (WINDOW_WIDTH, y))


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Project 1: A* Pathfinding")
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill(WHITE)
        draw_grid(screen)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()

"""
window.py
A PyGame window that stays sharp on high resolution screens (like a Mac's Retina display).

Normally PyGame draws 1 pixel per screen point. A Retina screen has 2 pixels
per point, so macOS stretches the picture to twice its size, which makes text
and lines look blurry. The fix is to ask SDL (the C library PyGame is built on)
for a "high DPI" window, draw everything on a canvas at the real pixel size,
and copy that canvas to the screen each frame.

pygame 2.6's own window functions never pass SDL the high DPI flag, so on macOS
this module creates the window by calling SDL directly through ctypes. On other
systems, or if anything goes wrong, it falls back to a normal pygame window
with a scale of 1, so the visualizer always runs.

AI use: this project is being developed through chats with Claude (Anthropic).
See "AI Use" in README.md. Saved chat logs showing how we worked: AI_CHAT_LOGS.md.
"""

import ctypes
import glob
import os

import pygame

# Constants from SDL2's headers (SDL_video.h, SDL_render.h, SDL_pixels.h).
SDL_WINDOW_SHOWN = 0x4
SDL_WINDOW_ALLOW_HIGHDPI = 0x2000
SDL_WINDOWPOS_CENTERED = 0x2FFF0000
SDL_RENDERER_ACCELERATED = 0x2
SDL_RENDERER_PRESENTVSYNC = 0x4
SDL_PIXELFORMAT_RGB888 = 0x16161804      # 32 bits per pixel laid out as 0x00RRGGBB
SDL_TEXTUREACCESS_STREAMING = 1
RGB888_MASKS = (0xFF0000, 0x00FF00, 0x0000FF, 0)

TITLE_BAR_H = 28   # height of the macOS title bar, in points


class _SDLRect(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int), ("w", ctypes.c_int), ("h", ctypes.c_int)]


def _load_sdl():
    """Load the same SDL2 library that pygame itself is using, and declare the functions we call.

    Loading the exact file pygame loaded gives back the library that is already
    in memory, so pygame and this module share one SDL (same events, same mouse).
    """
    found = glob.glob(os.path.join(os.path.dirname(pygame.__file__), ".dylibs", "libSDL2-2*.dylib"))
    if not found:
        raise OSError("pygame's SDL2 library was not found")
    sdl = ctypes.CDLL(found[0])
    p, i, u32 = ctypes.c_void_p, ctypes.c_int, ctypes.c_uint32
    int_ptr = ctypes.POINTER(ctypes.c_int)
    signatures = {
        "SDL_CreateWindow": (p, [ctypes.c_char_p, i, i, i, i, u32]),
        "SDL_CreateRenderer": (p, [p, i, u32]),
        "SDL_CreateTexture": (p, [p, u32, i, i, i]),
        "SDL_GetWindowSizeInPixels": (None, [p, int_ptr, int_ptr]),
        "SDL_UpdateTexture": (i, [p, p, p, i]),
        "SDL_RenderCopy": (i, [p, p, p, p]),
        "SDL_RenderPresent": (None, [p]),
        "SDL_RaiseWindow": (None, [p]),
        "SDL_DestroyTexture": (None, [p]),
        "SDL_DestroyRenderer": (None, [p]),
        "SDL_DestroyWindow": (None, [p]),
        "SDL_GetDisplayUsableBounds": (i, [i, ctypes.POINTER(_SDLRect)]),
    }
    for name, (restype, argtypes) in signatures.items():
        fn = getattr(sdl, name)
        fn.restype = restype
        fn.argtypes = argtypes
    return sdl


def usable_screen_size():
    """Room available for a window's contents in points: the screen minus the menu bar, Dock, and title bar."""
    try:
        sdl = _load_sdl()
        r = _SDLRect()
        if sdl.SDL_GetDisplayUsableBounds(0, ctypes.byref(r)) == 0 and r.w > 0:
            return r.w, r.h - TITLE_BAR_H
    except (OSError, AttributeError):
        pass
    w, h = pygame.display.get_desktop_sizes()[0]
    return w, h - 100   # rough allowance for a taskbar and title bar


class Window:
    """A window plus a canvas to draw on.

    Draw on `canvas`, then call present(). The canvas is `scale` times bigger
    than the window size in points (2 on a Retina screen, 1 elsewhere), so
    drawing code multiplies every coordinate by `scale`.
    """

    def __init__(self, title, size, offscreen_scale=None):
        """Open a window of `size` points. With offscreen_scale, only make a canvas (for screenshots)."""
        self.size = size
        self._sdl = None
        if offscreen_scale:
            self.scale = offscreen_scale
            self.canvas = pygame.Surface((size[0] * offscreen_scale, size[1] * offscreen_scale))
            return
        if pygame.display.get_driver() == "cocoa":
            try:
                self._open_high_dpi(title, size)
                return
            except (OSError, AttributeError, RuntimeError, ctypes.ArgumentError):
                self.close()   # fall back to a normal window below
        self.scale = 1
        self.canvas = pygame.display.set_mode(size)
        pygame.display.set_caption(title)

    def _open_high_dpi(self, title, size):
        """Create the SDL window, renderer, and texture by hand, with the high DPI flag set."""
        sdl = self._sdl = _load_sdl()
        self._win = self._ren = self._tex = None
        self._win = sdl.SDL_CreateWindow(title.encode(), SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
                                         size[0], size[1], SDL_WINDOW_SHOWN | SDL_WINDOW_ALLOW_HIGHDPI)
        if not self._win:
            raise RuntimeError("SDL_CreateWindow failed")
        self._ren = sdl.SDL_CreateRenderer(self._win, -1, SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC)
        if not self._ren:
            raise RuntimeError("SDL_CreateRenderer failed")

        # The window's real size in pixels tells us the screen's scale factor.
        pw, ph = ctypes.c_int(), ctypes.c_int()
        sdl.SDL_GetWindowSizeInPixels(self._win, ctypes.byref(pw), ctypes.byref(ph))
        self.scale = max(1, round(pw.value / size[0]))
        cw, ch = size[0] * self.scale, size[1] * self.scale

        # A streaming texture is GPU memory we overwrite with the canvas every frame.
        self._tex = sdl.SDL_CreateTexture(self._ren, SDL_PIXELFORMAT_RGB888, SDL_TEXTUREACCESS_STREAMING, cw, ch)
        if not self._tex:
            raise RuntimeError("SDL_CreateTexture failed")
        # Give the canvas the texture's exact pixel layout so it can be copied as is.
        self.canvas = pygame.Surface((cw, ch), 0, 32, RGB888_MASKS)
        sdl.SDL_RaiseWindow(self._win)

    def present(self):
        """Show what has been drawn on the canvas."""
        if self._sdl:
            self._sdl.SDL_UpdateTexture(self._tex, None, self.canvas._pixels_address, self.canvas.get_pitch())
            self._sdl.SDL_RenderCopy(self._ren, self._tex, None, None)
            self._sdl.SDL_RenderPresent(self._ren)
        elif pygame.display.get_surface() is not None:
            pygame.display.flip()

    def close(self):
        """Free the SDL objects created by hand (a normal pygame window closes itself)."""
        if not self._sdl:
            return
        if self._tex:
            self._sdl.SDL_DestroyTexture(self._tex)
        if self._ren:
            self._sdl.SDL_DestroyRenderer(self._ren)
        if self._win:
            self._sdl.SDL_DestroyWindow(self._win)
        self._sdl = None

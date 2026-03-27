'''
project.py — Desktop GUI (Redesigned)
======================================
Terminal-chic aesthetic: monospace fonts, teal/green accents, dark palette.
Animations: frame pop-in, button press scale, stats number lerp, title shimmer.
Reorganized layout: sidebar stats left, memory top-right, table bottom-right.
'''

import pygame
import sys
import math

from main import (
    PagingSimulator,
    SegmentationSimulator,
    VirtualMemorySimulator,
    parse_paging_input,
    parse_segmentation_input,
)

# ---------------------------------------------------------------------------
# Window & theme constants
# ---------------------------------------------------------------------------

WIDTH, HEIGHT = 1040, 720

# Dark terminal palette
BG_COLOR       = (13,  15,  18)
PANEL_COLOR    = (18,  22,  28)
PANEL_ALT      = (22,  27,  35)
TEXT_COLOR     = (210, 225, 215)
MUTED_COLOR    = (90,  110, 100)
BORDER_COLOR   = (35,  50,  42)
BORDER_BRIGHT  = (55,  80,  65)

# Accent colours — teal/green terminal
TEAL           = (0,   210, 160)
TEAL_DIM       = (0,   120,  90)
TEAL_DARK      = (0,    45,  35)
GREEN_BRIGHT   = (80,  230, 130)
GREEN_DIM      = (30,  100,  55)
AMBER          = (255, 185,  40)
AMBER_DIM      = (120,  75,  10)
RED_ACCENT     = (220,  70,  70)
RED_DIM        = ( 80,  25,  25)
BLUE_SWAP      = ( 50, 130, 200)
BLUE_SWAP_DIM  = ( 20,  50,  90)

# Buttons
BTN_NORMAL     = (22,  30,  27)
BTN_HOVER      = (30,  48,  40)
BTN_ACTIVE     = (0,   60,  48)
BTN_BORDER_ACT = TEAL

# Input
INPUT_NORMAL   = (16,  22,  20)
INPUT_ACTIVE   = (18,  30,  26)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("› memory visualizer")

# Monospace fonts — terminal chic
def _mono(size, bold=False):
    for name in ("Consolas", "Courier New", "DejaVu Sans Mono", "monospace"):
        f = pygame.font.SysFont(name, size, bold=bold)
        if f:
            return f
    return pygame.font.SysFont(None, size, bold=bold)

FONT_TITLE  = _mono(22, bold=True)
FONT_LABEL  = _mono(14, bold=True)
FONT_BODY   = _mono(13)
FONT_SMALL  = _mono(12)
FONT_TINY   = _mono(11)
FONT_BIG    = _mono(26, bold=True)


# ---------------------------------------------------------------------------
# Utility: draw helpers
# ---------------------------------------------------------------------------

def _lerp(a, b, t):
    return a + (b - a) * t

def _lerp_color(c1, c2, t):
    return tuple(int(_lerp(c1[i], c2[i], t)) for i in range(3))

def _draw_rounded_rect_border(surface, color, rect, radius=6, width=1):
    pygame.draw.rect(surface, color, rect, width, border_radius=radius)

def _draw_filled_rounded(surface, color, rect, radius=6):
    pygame.draw.rect(surface, color, rect, border_radius=radius)

def _glow_rect(surface, color, rect, radius=6, alpha=60, spread=4):
    """Draw a soft glow halo around a rect using alpha surfaces."""
    glow_rect = pygame.Rect(
        rect.x - spread, rect.y - spread,
        rect.width + spread * 2, rect.height + spread * 2
    )
    glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
    glow_color = (*color, alpha)
    pygame.draw.rect(glow_surf, glow_color, glow_surf.get_rect(), border_radius=radius + spread)
    surface.blit(glow_surf, (glow_rect.x, glow_rect.y))

def _draw_panel(surface, rect, title="", accent=False):
    _draw_filled_rounded(surface, PANEL_COLOR, rect, radius=8)
    border_col = BORDER_BRIGHT if accent else BORDER_COLOR
    _draw_rounded_rect_border(surface, border_col, rect, radius=8, width=1)
    if title:
        # Title tab at top-left
        t = FONT_TINY.render(title.upper(), True, TEAL if accent else MUTED_COLOR)
        surface.blit(t, (rect.x + 12, rect.y + 10))
        # Underline
        line_y = rect.y + 26
        pygame.draw.line(surface, BORDER_COLOR,
                         (rect.x + 10, line_y), (rect.right - 10, line_y), 1)


# ---------------------------------------------------------------------------
# Animation helpers
# ---------------------------------------------------------------------------

class Animator:
    """Generic float animator, ease-out."""
    def __init__(self, initial=0.0, speed=0.12):
        self.value   = float(initial)
        self.target  = float(initial)
        self.speed   = speed

    def set_target(self, t):
        self.target = float(t)

    def tick(self):
        self.value = _lerp(self.value, self.target, self.speed)
        if abs(self.value - self.target) < 0.001:
            self.value = self.target

    @property
    def done(self):
        return abs(self.value - self.target) < 0.005


class FrameAnimator:
    """Tracks a pop-in scale (0→1) for each frame cell."""
    def __init__(self, n):
        self._scales = [Animator(1.0, speed=0.18) for _ in range(n)]
        self._prev   = [None] * n

    def notify_state(self, frames):
        """Call each frame with current occupant list to detect new arrivals."""
        if len(frames) != len(self._prev):
            self._scales = [Animator(1.0, speed=0.18) for _ in range(len(frames))]
            self._prev   = [None] * len(frames)
        for i, occ in enumerate(frames):
            if occ is not None and self._prev[i] is None:
                self._scales[i].value  = 0.0
                self._scales[i].target = 1.0
            elif occ is None and self._prev[i] is not None:
                self._scales[i].value  = 0.85
                self._scales[i].target = 1.0
        self._prev = list(frames)

    def tick_all(self):
        for a in self._scales:
            a.tick()

    def scale(self, i):
        if i < len(self._scales):
            return max(0.0, min(1.0, self._scales[i].value))
        return 1.0


# ---------------------------------------------------------------------------
# Reusable UI widgets
# ---------------------------------------------------------------------------

class Button:
    PRESS_DUR = 8   # frames the press-scale effect lasts

    def __init__(self, x, y, w, h, label, active_flag=False, accent=False):
        self.rect        = pygame.Rect(x, y, w, h)
        self.label       = label
        self.selected    = False
        self.accent      = accent          # primary action button style
        self._press_t    = 0               # countdown for press animation
        self._scale_anim = Animator(1.0, speed=0.25)

    def draw(self, surface):
        self._scale_anim.tick()

        hovered = self.rect.collidepoint(pygame.mouse.get_pos())
        pressing = self._press_t > 0
        if pressing:
            self._press_t -= 1

        if self.selected:
            bg = BTN_ACTIVE
            border = BTN_BORDER_ACT
        elif self.accent:
            bg = (0, 48, 38)
            border = TEAL_DIM
        elif hovered:
            bg = BTN_HOVER
            border = BORDER_BRIGHT
        else:
            bg = BTN_NORMAL
            border = BORDER_COLOR

        sc = self._scale_anim.value
        w2 = int(self.rect.width  * sc)
        h2 = int(self.rect.height * sc)
        dx = (self.rect.width  - w2) // 2
        dy = (self.rect.height - h2) // 2
        draw_r = pygame.Rect(self.rect.x + dx, self.rect.y + dy, w2, h2)

        if self.selected or (hovered and not pressing):
            _glow_rect(surface, TEAL, self.rect, alpha=25, spread=3)

        _draw_filled_rounded(surface, bg, draw_r, radius=5)
        _draw_rounded_rect_border(surface, border, draw_r, radius=5, width=1)

        label_color = TEAL if self.selected else (TEXT_COLOR if not self.accent else TEAL)
        prefix = "› " if self.selected else "  "
        text = FONT_BODY.render(prefix + self.label, True, label_color)
        surface.blit(text, text.get_rect(center=draw_r.center))

    def is_clicked(self, event):
        if (event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and self.rect.collidepoint(event.pos)):
            self._scale_anim.value  = 0.92
            self._scale_anim.target = 1.0
            self._press_t = self.PRESS_DUR
            return True
        return False


class TextInput:
    def __init__(self, x, y, w, h, placeholder=""):
        self.rect        = pygame.Rect(x, y, w, h)
        self.placeholder = placeholder
        self.text        = ""
        self.active      = False
        self._cursor_t   = 0
        self._glow_anim  = Animator(0.0, speed=0.1)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            was = self.active
            self.active = self.rect.collidepoint(event.pos)
            self._glow_anim.set_target(1.0 if self.active else 0.0)
        if self.active and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.active = False
                self._glow_anim.set_target(0.0)
                return self.text
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                self.text += event.unicode
        return None

    def draw(self, surface):
        self._glow_anim.tick()
        self._cursor_t = (self._cursor_t + 1) % 60

        if self._glow_anim.value > 0.05:
            _glow_rect(surface, TEAL, self.rect,
                       alpha=int(40 * self._glow_anim.value), spread=4)

        bg = INPUT_ACTIVE if self.active else INPUT_NORMAL
        border = _lerp_color(BORDER_COLOR, TEAL, self._glow_anim.value)
        _draw_filled_rounded(surface, bg, self.rect, radius=5)
        _draw_rounded_rect_border(surface, border, self.rect, radius=5, width=1)

        display   = self.text   if self.text   else self.placeholder
        txt_color = TEXT_COLOR  if self.text   else MUTED_COLOR
        rendered  = FONT_BODY.render(display, True, txt_color)
        ty = self.rect.y + (self.rect.h - rendered.get_height()) // 2
        surface.blit(rendered, (self.rect.x + 10, ty))

        if self.active and self._cursor_t < 30:
            cx = self.rect.x + 10 + rendered.get_width() + 2
            pygame.draw.line(surface, TEAL,
                             (cx, self.rect.y + 6), (cx, self.rect.bottom - 6), 1)

    def clear(self):
        self.text   = ""
        self.active = False
        self._glow_anim.set_target(0.0)


# ---------------------------------------------------------------------------
# Stats lerp state
# ---------------------------------------------------------------------------

class LerpStat:
    def __init__(self):
        self._display = Animator(0.0, speed=0.08)

    def update(self, target_int):
        self._display.set_target(float(target_int))

    def tick(self):
        self._display.tick()

    @property
    def shown(self):
        return int(round(self._display.value))


# ---------------------------------------------------------------------------
# Drawing functions
# ---------------------------------------------------------------------------

def _draw_frame_cell(surface, rect, occupant, scale, is_fault, flash_t):
    """Draw a single memory frame cell with pop-in scale animation."""
    if scale < 0.02:
        return

    # Scaled rect centred on original
    sw = max(4, int(rect.width  * scale))
    sh = max(4, int(rect.height * scale))
    dx = (rect.width  - sw) // 2
    dy = (rect.height - sh) // 2
    r  = pygame.Rect(rect.x + dx, rect.y + dy, sw, sh)

    # Colour logic
    if is_fault and flash_t > 0:
        t = flash_t / 30.0
        color  = _lerp_color(AMBER_DIM, AMBER, t)
        border = _lerp_color(AMBER_DIM, AMBER, t)
        _glow_rect(surface, AMBER, r, alpha=int(60 * t), spread=4)
    elif occupant:
        color  = GREEN_DIM
        border = GREEN_BRIGHT
        _glow_rect(surface, GREEN_BRIGHT, r, alpha=20, spread=3)
    else:
        color  = (16, 24, 20)
        border = BORDER_COLOR

    _draw_filled_rounded(surface, color, r, radius=4)
    _draw_rounded_rect_border(surface, border, r, radius=4, width=1)

    if scale < 0.6:
        return   # don't draw text during pop-in

    # Frame index
    fidx_text = FONT_TINY.render(f"F{rect.x}", True, MUTED_COLOR)   # placeholder — overridden below
    # (text drawn by caller who knows the index)


def draw_paging_frames(surface, state, flash_timer, rect, frame_anim):
    _draw_panel(surface, rect, "Memory Frames", accent=True)
    frames = state["frames"]
    n = len(frames)
    if n == 0:
        return
    frame_anim.notify_state(frames)
    frame_anim.tick_all()

    pad    = 12
    cell_w = (rect.width - pad * 2) // n
    cell_h = 48
    top    = rect.y + 32

    for i, occupant in enumerate(frames):
        x  = rect.x + pad + i * cell_w
        sc = frame_anim.scale(i)
        is_fault = (state["last_fault_frame"] == i and flash_timer > 0)

        sw = max(4, int((cell_w - 4) * sc))
        sh = max(4, int(cell_h      * sc))
        dx = ((cell_w - 4) - sw) // 2
        dy = (cell_h - sh) // 2
        r  = pygame.Rect(x + dx, top + dy, sw, sh)

        if is_fault and flash_timer > 0:
            t = flash_timer / 30.0
            color  = _lerp_color(AMBER_DIM, AMBER, t)
            border = AMBER
            _glow_rect(surface, AMBER, r, alpha=int(70 * t), spread=5)
        elif occupant:
            color  = GREEN_DIM
            border = GREEN_BRIGHT
            _glow_rect(surface, GREEN_BRIGHT, r, alpha=18, spread=3)
        else:
            color  = (14, 20, 17)
            border = BORDER_COLOR

        _draw_filled_rounded(surface, color, r, radius=4)
        _draw_rounded_rect_border(surface, border, r, radius=4, width=1)

        if sc > 0.55:
            fi = FONT_TINY.render(f"F{i}", True,
                                  MUTED_COLOR if not occupant else TEAL)
            surface.blit(fi, (r.x + 3, r.y + 2))
            if occupant:
                pid, pn = occupant
                l1 = FONT_TINY.render(f"P{pid}", True, TEXT_COLOR)
                l2 = FONT_TINY.render(f"p{pn}", True, GREEN_BRIGHT)
                surface.blit(l1, (r.x + 3, r.y + 14))
                surface.blit(l2, (r.x + 3, r.y + 26))


def draw_segmentation_frames(surface, state, flash_timer, rect, frame_anim):
    _draw_panel(surface, rect, "Memory Segments", accent=True)
    total_mem = 32
    bar_top   = rect.y + 32
    bar_h     = 48
    pad       = 12
    avail_w   = rect.width - pad * 2
    px_per_kb = avail_w / total_mem
    last      = state["last_allocation"]

    for base, size, pid, sid in state["memory_state"]:
        x  = rect.x + pad + int(base * px_per_kb)
        w  = max(int(size * px_per_kb) - 2, 4)
        is_new = last and last[0] == base and flash_timer > 0
        t  = (flash_timer / 30.0) if is_new else 0
        color  = _lerp_color(GREEN_DIM, AMBER, t)
        border = _lerp_color(GREEN_BRIGHT, AMBER, t)
        bar = pygame.Rect(x, bar_top, w, bar_h)
        _draw_filled_rounded(surface, color, bar, radius=4)
        _draw_rounded_rect_border(surface, border, bar, radius=4, width=1)
        if is_new:
            _glow_rect(surface, AMBER, bar, alpha=int(60 * t), spread=4)
        elif w > 10:
            _glow_rect(surface, GREEN_BRIGHT, bar, alpha=15, spread=2)
        if w > 22:
            lbl = FONT_TINY.render(f"P{pid}S{sid}", True, TEXT_COLOR)
            surface.blit(lbl, (x + 3, bar_top + (bar_h - lbl.get_height()) // 2))

    for base, size in state["free_blocks"]:
        x = rect.x + pad + int(base * px_per_kb)
        w = max(int(size * px_per_kb) - 2, 2)
        bar = pygame.Rect(x, bar_top, w, bar_h)
        _draw_filled_rounded(surface, (14, 20, 17), bar, radius=4)
        _draw_rounded_rect_border(surface, BORDER_COLOR, bar, radius=4, width=1)


def draw_virtual_frames(surface, state, flash_timer, rect, frame_anim):
    _draw_panel(surface, rect, "RAM + Swap", accent=True)
    frames = state["memory_frames"]
    n      = len(frames)
    pad    = 12

    frame_anim.notify_state(frames)
    frame_anim.tick_all()

    # RAM row
    if n > 0:
        cell_w = (rect.width - pad * 2) // n
        cell_h = 38
        top    = rect.y + 32
        for i, occupant in enumerate(frames):
            x  = rect.x + pad + i * cell_w
            sc = frame_anim.scale(i)
            is_fault = (state["last_fault_frame"] == i and flash_timer > 0)

            sw = max(4, int((cell_w - 3) * sc))
            sh = max(4, int(cell_h * sc))
            dx = ((cell_w - 3) - sw) // 2
            dy = (cell_h - sh) // 2
            r  = pygame.Rect(x + dx, top + dy, sw, sh)

            if is_fault and flash_timer > 0:
                t = flash_timer / 30.0
                color  = _lerp_color(AMBER_DIM, AMBER, t)
                border = AMBER
                _glow_rect(surface, AMBER, r, alpha=int(70 * t), spread=4)
            elif occupant:
                color  = GREEN_DIM
                border = GREEN_BRIGHT
                _glow_rect(surface, GREEN_BRIGHT, r, alpha=18, spread=2)
            else:
                color  = (14, 20, 17)
                border = BORDER_COLOR

            _draw_filled_rounded(surface, color, r, radius=3)
            _draw_rounded_rect_border(surface, border, r, radius=3, width=1)
            if sc > 0.55:
                fi = FONT_TINY.render(f"F{i}", True, MUTED_COLOR if not occupant else TEAL)
                surface.blit(fi, (r.x + 2, r.y + 2))
                if occupant:
                    pid, pn = occupant
                    lbl = FONT_TINY.render(f"{pn}", True, GREEN_BRIGHT)
                    surface.blit(lbl, (r.x + 2, r.y + 16))

    # Swap label
    swap_lbl = FONT_TINY.render("SWAP", True, MUTED_COLOR)
    surface.blit(swap_lbl, (rect.x + pad, rect.y + 80))
    pygame.draw.line(surface, BORDER_COLOR,
                     (rect.x + pad + 38, rect.y + 86),
                     (rect.right - pad, rect.y + 86), 1)

    swap = state["swap_space"]
    m    = len(swap)
    if m > 0:
        sw2  = (rect.width - pad * 2) // m
        stop = rect.y + 94
        for i, occupant in enumerate(swap):
            x = rect.x + pad + i * sw2
            color  = BLUE_SWAP_DIM if occupant else (12, 18, 16)
            border = BLUE_SWAP if occupant else BORDER_COLOR
            cell   = pygame.Rect(x, stop, sw2 - 2, 28)
            _draw_filled_rounded(surface, color, cell, radius=3)
            _draw_rounded_rect_border(surface, border, cell, radius=3, width=1)
            if occupant and sw2 > 16:
                pid, pn = occupant
                lbl = FONT_TINY.render(f"{pn}", True, BLUE_SWAP)
                surface.blit(lbl, (x + 2, stop + 8))


def draw_page_table(surface, state, mode, rect, scroll):
    title = "Page Table" if mode != "Segmentation" else "Segment Table"
    _draw_panel(surface, rect, title)

    # ── Mode-specific banner ─────────────────────────────────────────────────
    BANNERS = {
        "Paging": (
            "Each page maps to a RAM frame. "
            "PAGE FAULT = RAM full → oldest frame evicted (FIFO) or least-used (LRU). "
            "Cold misses (free frame available) are not counted as faults."
        ),
        "Segmentation": (
            "Variable-size segments placed by first-fit. "
            "Each row shows seg id → base address and size in KB. "
            "Eviction occurs when no contiguous block fits the new segment."
        ),
        "Virtual Memory": (
            "New pages stage to SWAP first, then swap-in to RAM on access. "
            "PAGE FAULT = RAM full → victim evicted to swap (swap-out). "
            "Green = in RAM  |  Cyan = in Swap  |  Fault only on eviction."
        ),
    }
    banner_text = BANNERS.get(mode, "")
    # Draw banner as word-wrapped lines inside a tinted box
    banner_y = rect.y + 30
    banner_h = 34
    br = pygame.Rect(rect.x + 6, banner_y, rect.width - 12, banner_h)
    _draw_filled_rounded(surface, (18, 28, 24), br, radius=4)
    _draw_rounded_rect_border(surface, BORDER_COLOR, br, radius=4, width=1)

    # Truncate to single line that fits
    max_w = br.width - 16
    truncated = banner_text
    rendered_b = FONT_TINY.render(truncated, True, MUTED_COLOR)
    while rendered_b.get_width() > max_w and len(truncated) > 10:
        truncated = truncated[:-4] + "…"
        rendered_b = FONT_TINY.render(truncated, True, MUTED_COLOR)
    surface.blit(rendered_b, (br.x + 8, br.y + 6))

    # Second line if banner is long
    if len(banner_text) > len(truncated):
        rest = banner_text[len(truncated.rstrip("…")):]
        rest_r = FONT_TINY.render(rest.strip(), True, MUTED_COLOR)
        if rest_r.get_width() <= max_w:
            surface.blit(rest_r, (br.x + 8, br.y + 19))

    # ── Last action status for VM ─────────────────────────────────────────
    banner_offset = banner_h + 8

    entries = []
    if mode == "Paging":
        for pid, pages in state["page_table"].items():
            for pn, frame in pages:
                loc = f"Frame {frame:>2}" if frame != -1 else "  Disk  "
                entries.append((f"P{pid}", f"pg {pn:>2}", "→", loc, frame != -1))
    elif mode == "Segmentation":
        for pid, segs in state["segment_table"].items():
            for proc_id, sid, size, base in segs:
                entries.append((f"P{proc_id}", f"seg {sid}", "→",
                                 f"base {base:>2}  ({size} KB)", True))
    else:  # Virtual Memory
        # Build a map of what's in swap
        swap_map = {}  # page -> swap_idx
        for si, occ in enumerate(state.get("swap_space", [])):
            if occ is not None:
                pid_s, pn_s = occ
                swap_map[(str(pid_s), int(pn_s))] = si

        for pid, pages in state["page_table"].items():
            for pn, loc_idx, in_ram in pages:
                if in_ram:
                    loc = f"RAM  {loc_idx:>2}"
                    in_mem = True
                else:
                    loc = f"Swap {loc_idx:>2}"
                    in_mem = False
                entries.append((f"P{pid}", f"pg {pn:>2}", "→", loc, in_mem))

        # Also add pages that are in swap but not yet in the page_table
        # (staged pages before any RAM load)
        tracked_pages = set()
        for pid, pages in state["page_table"].items():
            for pn, _, __ in pages:
                tracked_pages.add((str(pid), int(pn)))
        for (pid_s, pn_s), si in swap_map.items():
            if (pid_s, pn_s) not in tracked_pages:
                entries.append((f"P{pid_s}", f"pg {pn_s:>2}", "→", f"Swap {si:>2}", False))

    row_h   = 20
    inner_y = rect.y + 34 + banner_offset
    visible = (rect.height - 40 - banner_offset) // row_h
    max_sc  = max(0, len(entries) - visible)
    scroll  = max(0, min(scroll, max_sc))

    clip = pygame.Rect(rect.x + 4, inner_y, rect.width - 8, rect.height - 38)
    surface.set_clip(clip)

    for i, entry in enumerate(entries[scroll: scroll + visible]):
        y   = inner_y + i * row_h
        pid_s, key_s, arr, val_s, in_mem = entry

        # Alternating row tint
        if i % 2 == 0:
            row_r = pygame.Rect(rect.x + 6, y, rect.width - 12, row_h - 1)
            _draw_filled_rounded(surface, PANEL_ALT, row_r, radius=3)

        x = rect.x + 12
        pid_surf = FONT_TINY.render(pid_s,  True, TEAL)
        key_surf = FONT_TINY.render(key_s,  True, TEXT_COLOR)
        arr_surf = FONT_TINY.render(arr,    True, MUTED_COLOR)
        # Green for RAM, blue for Swap, muted for Disk
        if in_mem:
            val_col = GREEN_BRIGHT
        elif "Swap" in val_s:
            val_col = BLUE_SWAP
        else:
            val_col = MUTED_COLOR
        val_surf = FONT_TINY.render(val_s,  True, val_col)

        surface.blit(pid_surf, (x,       y + 4))
        surface.blit(key_surf, (x + 32,  y + 4))
        surface.blit(arr_surf, (x + 80,  y + 4))
        surface.blit(val_surf, (x + 100, y + 4))

    surface.set_clip(None)

    # Scroll indicators
    if len(entries) > visible:
        for up, cond, yy in [
            (True,  scroll > 0,        inner_y + 2),
            (False, scroll < max_sc,   rect.bottom - 14),
        ]:
            color = TEAL if cond else BORDER_COLOR
            cx = rect.right - 14
            if up:
                pts = [(cx, yy + 2), (cx - 5, yy + 9), (cx + 5, yy + 9)]
            else:
                pts = [(cx, yy + 9), (cx - 5, yy + 2), (cx + 5, yy + 2)]
            pygame.draw.polygon(surface, color, pts)

    return scroll


def draw_stats_panel(surface, state, mode, algorithm, status, rect,
                     lerp_faults, lerp_swaps, lerp_mem):
    _draw_panel(surface, rect)

    # ── Header ──────────────────────────────────────────────────────────────
    hdr = FONT_LABEL.render("SYS", True, TEAL)
    surface.blit(hdr, (rect.x + 12, rect.y + 10))

    y = rect.y + 36
    pad = 12

    def stat_card(label, value, vy, color=TEXT_COLOR, big=False):
        """Draw a mini stat card."""
        cr = pygame.Rect(rect.x + pad, vy, rect.width - pad * 2, 46)
        _draw_filled_rounded(surface, PANEL_ALT, cr, radius=5)
        _draw_rounded_rect_border(surface, BORDER_COLOR, cr, radius=5, width=1)

        lbl_s = FONT_TINY.render(label.upper(), True, MUTED_COLOR)
        surface.blit(lbl_s, (cr.x + 8, cr.y + 6))

        font  = FONT_BIG if big else FONT_LABEL
        val_s = font.render(str(value), True, color)
        surface.blit(val_s, (cr.x + 8, cr.y + 20))

    def pill(label, active, vx, vy, w=60, h=22):
        pr = pygame.Rect(vx, vy, w, h)
        if active:
            _draw_filled_rounded(surface, TEAL_DARK, pr, radius=11)
            _draw_rounded_rect_border(surface, TEAL, pr, radius=11, width=1)
            _glow_rect(surface, TEAL, pr, alpha=25, spread=3)
            tc = TEAL
        else:
            _draw_filled_rounded(surface, BTN_NORMAL, pr, radius=11)
            _draw_rounded_rect_border(surface, BORDER_COLOR, pr, radius=11, width=1)
            tc = MUTED_COLOR
        ls = FONT_TINY.render(label, True, tc)
        surface.blit(ls, ls.get_rect(center=pr.center))

    # Mode & algo pills
    modes = [("PAGING", mode == "Paging"),
             ("SEG",    mode == "Segmentation"),
             ("VMEM",   mode == "Virtual Memory")]
    pill_w = (rect.width - pad * 2 - 8) // 3
    for mi, (ml, active) in enumerate(modes):
        pill(ml, active, rect.x + pad + mi * (pill_w + 4), y, w=pill_w)
    y += 30

    algos = [("FIFO", algorithm == "FIFO"), ("LRU", algorithm == "LRU")]
    for ai, (al, active) in enumerate(algos):
        pill(al, active, rect.x + pad + ai * ((pill_w + 4) * 3 // 2 + 4), y, w=68)
    y += 34

    # Lerp stat updates
    lerp_mem.tick()
    mem_pct = state.get("memory_used_pct", 0)
    lerp_mem.update(mem_pct)

    # Memory bar
    bar_r = pygame.Rect(rect.x + pad, y, rect.width - pad * 2, 8)
    _draw_filled_rounded(surface, (20, 30, 25), bar_r, radius=4)
    fill_w = int(bar_r.width * lerp_mem.shown / 100)
    if fill_w > 0:
        fill_r = pygame.Rect(bar_r.x, bar_r.y, fill_w, bar_r.height)
        fill_col = RED_ACCENT if lerp_mem.shown > 80 else (AMBER if lerp_mem.shown > 50 else TEAL)
        _draw_filled_rounded(surface, fill_col, fill_r, radius=4)
    mem_lbl = FONT_TINY.render(f"MEM  {lerp_mem.shown}%", True, MUTED_COLOR)
    surface.blit(mem_lbl, (rect.x + pad, y + 12))
    y += 30

    # Stat cards
    if mode == "Paging":
        lerp_faults.tick(); lerp_faults.update(state["page_faults"])
        stat_card("Page Faults",  lerp_faults.shown, y, AMBER if lerp_faults.shown > 0 else TEXT_COLOR, big=True)
        y += 54
    elif mode == "Segmentation":
        lerp_faults.tick(); lerp_faults.update(state["allocation_failures"])
        stat_card("Alloc Fails",  lerp_faults.shown, y, RED_ACCENT if lerp_faults.shown > 0 else TEXT_COLOR, big=True)
        y += 54
    else:
        lerp_faults.tick(); lerp_faults.update(state["page_faults"])
        lerp_swaps.tick();  lerp_swaps.update(state["swap_operations"])
        stat_card("Page Faults",  lerp_faults.shown, y, AMBER if lerp_faults.shown > 0 else TEXT_COLOR, big=True)
        y += 54
        stat_card("Swap Ops",     lerp_swaps.shown, y, BLUE_SWAP if lerp_swaps.shown > 0 else TEXT_COLOR, big=True)
        y += 54

    # Status pill (bottom of panel)
    status_map = {
        "Ready":    (MUTED_COLOR,   "◉ READY"),
        "Running":  (TEAL,          "◉ RUNNING"),
        "Finished": (GREEN_BRIGHT,  "◉ DONE"),
        "Paused":   (AMBER,         "◉ PAUSED"),
    }
    sc, st_text = status_map.get(status, (RED_ACCENT, f"◉ {status.upper()}"))

    # clamp y to fit inside panel
    y = min(y, rect.bottom - 34)
    sr = pygame.Rect(rect.x + pad, y, rect.width - pad * 2, 26)
    _draw_filled_rounded(surface, PANEL_ALT, sr, radius=13)
    _draw_rounded_rect_border(surface, sc, sr, radius=13, width=1)
    _glow_rect(surface, sc, sr, alpha=20, spread=3)
    ss = FONT_TINY.render(st_text, True, sc)
    surface.blit(ss, ss.get_rect(center=sr.center))


def draw_title_bar(surface, step, total, tick):
    """Shimmer title + progress bar."""
    title_str = "› MEMORY VISUALIZER"
    base_color = TEXT_COLOR

    # Shimmer: highlight drifts across characters
    shimmer_pos = (tick * 0.4) % (len(title_str) + 10)

    x_cursor = WIDTH // 2 - FONT_TITLE.size(title_str)[0] // 2
    y = 14
    for ci, ch in enumerate(title_str):
        dist    = abs(ci - shimmer_pos)
        t       = max(0.0, 1.0 - dist / 4.0)
        color   = _lerp_color(MUTED_COLOR, TEAL, t)
        cs      = FONT_TITLE.render(ch, True, color)
        surface.blit(cs, (x_cursor, y))
        x_cursor += cs.get_width()

    # Thin progress bar under title
    bar_y  = y + FONT_TITLE.get_height() + 4
    bar_x  = 60
    bar_w  = WIDTH - 120
    pygame.draw.line(surface, BORDER_COLOR, (bar_x, bar_y), (bar_x + bar_w, bar_y), 1)
    if total > 0:
        fill = int(bar_w * step / total)
        pygame.draw.line(surface, TEAL, (bar_x, bar_y), (bar_x + fill, bar_y), 2)
        prog = FONT_TINY.render(f"step {step}/{total}", True, MUTED_COLOR)
        surface.blit(prog, (bar_x + bar_w + 6, bar_y - 5))


def draw_controls(surface, rect):
    _draw_filled_rounded(surface, PANEL_COLOR, rect, radius=0)
    pygame.draw.line(surface, BORDER_BRIGHT, (rect.x, rect.y), (rect.right, rect.y), 1)


def draw_error(surface, msg, x, y):
    if not msg:
        return
    lbl = FONT_TINY.render("⚠ " + msg, True, AMBER)
    surface.blit(lbl, (x, y))


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

TITLE_H  = 52
CTRL_H   = 92          # row1(18+32) + gap(8) + row2(26) + padding(8) = 92
MID_H    = HEIGHT - TITLE_H - CTRL_H

SIDEBAR_W = 210
MEM_H     = 170
TABLE_H   = MID_H - MEM_H - 6

sidebar_rect = pygame.Rect(8,            TITLE_H + 4, SIDEBAR_W,       MID_H - 8)
mem_rect     = pygame.Rect(SIDEBAR_W+14, TITLE_H + 4, WIDTH-SIDEBAR_W-22, MEM_H)
table_rect   = pygame.Rect(SIDEBAR_W+14, TITLE_H + MEM_H + 10, WIDTH-SIDEBAR_W-22, TABLE_H - 6)
ctrl_rect    = pygame.Rect(0,            HEIGHT - CTRL_H,         WIDTH,   CTRL_H)


# ---------------------------------------------------------------------------
# Main application loop
# ---------------------------------------------------------------------------

def run():
    clock   = pygame.time.Clock()
    running = True
    tick    = 0

    # Simulators
    paging_sim = PagingSimulator()
    seg_sim    = SegmentationSimulator()
    vm_sim     = VirtualMemorySimulator()

    # App state
    mode      = "Paging"
    algorithm = "FIFO"
    status    = "Ready"
    sequence  = []
    step      = 0
    flash_timer = 0
    scroll    = 0
    error_msg = ""

    paging_state = paging_sim.get_state()
    seg_state    = seg_sim.get_state()
    vm_state     = vm_sim.get_state()

    # Animators
    paging_frame_anim = FrameAnimator(paging_sim.num_frames)
    vm_frame_anim     = FrameAnimator(vm_sim.num_frames)

    lerp_faults = LerpStat()
    lerp_swaps  = LerpStat()
    lerp_mem    = LerpStat()

    def active_state():
        if mode == "Paging":       return paging_state
        if mode == "Segmentation": return seg_state
        return vm_state

    def refresh_states():
        nonlocal paging_state, seg_state, vm_state
        paging_state = paging_sim.get_state()
        seg_state    = seg_sim.get_state()
        vm_state     = vm_sim.get_state()

    # Widgets — row1 at +10, row2 at +52  (10+32+10=52, 52+26+4=82 < 92)
    seq_input = TextInput(12, HEIGHT - CTRL_H + 10, 300, 32,
                          placeholder="e.g. 0,1,2 or 0:4,1:8")

    btn_start  = Button(320, HEIGHT - CTRL_H + 10, 72, 32, "Start",  accent=True)
    btn_step   = Button(400, HEIGHT - CTRL_H + 10, 72, 32, "Step",   accent=True)
    btn_reset  = Button(480, HEIGHT - CTRL_H + 10, 72, 32, "Reset")

    btn_paging = Button(12,  HEIGHT - CTRL_H + 52, 100, 26, "Paging",  active_flag=True)
    btn_seg    = Button(118, HEIGHT - CTRL_H + 52, 130, 26, "Segmentation", active_flag=True)
    btn_vm     = Button(254, HEIGHT - CTRL_H + 52, 110, 26, "Virtual Mem",  active_flag=True)
    btn_fifo   = Button(380, HEIGHT - CTRL_H + 52, 70,  26, "FIFO",   active_flag=True)
    btn_lru    = Button(456, HEIGHT - CTRL_H + 52, 70,  26, "LRU",    active_flag=True)

    mode_btns = [btn_paging, btn_seg, btn_vm]
    algo_btns = [btn_fifo, btn_lru]

    def _update_buttons():
        btn_paging.selected = (mode == "Paging")
        btn_seg.selected    = (mode == "Segmentation")
        btn_vm.selected     = (mode == "Virtual Memory")
        btn_fifo.selected   = (algorithm == "FIFO")
        btn_lru.selected    = (algorithm == "LRU")

    _update_buttons()

    def do_start():
        nonlocal sequence, step, status, error_msg, flash_timer, scroll
        error_msg = ""
        raw = seq_input.text.strip()
        if not raw:
            error_msg = "Enter a sequence first."
            return
        try:
            if mode in ("Paging", "Virtual Memory"):
                sequence = parse_paging_input(raw)
            else:
                sequence = parse_segmentation_input(raw)
        except ValueError as e:
            error_msg = str(e)
            return
        step = 0; flash_timer = 0; scroll = 0; status = "Running"

    def do_step():
        nonlocal step, status, flash_timer, error_msg
        nonlocal paging_state, seg_state, vm_state
        error_msg = ""
        if not sequence or step >= len(sequence):
            status = "Finished" if sequence else "Ready"
            return
        try:
            if mode == "Paging":
                pid, pn = sequence[step]
                paging_sim.simulate_page_request(pid, pn)
                paging_state = paging_sim.get_state()
                flash_timer  = 30 if paging_state["last_fault_frame"] is not None else 0
            elif mode == "Segmentation":
                pid, sid, size = sequence[step]
                ok = seg_sim.allocate_segment(pid, sid, size)
                seg_state   = seg_sim.get_state()
                flash_timer = 30 if seg_state["last_allocation"] else 0
                if not ok:
                    error_msg = f"Seg {sid} ({size} KB) — not enough memory."
            else:
                pid, pn = sequence[step]
                vm_sim.simulate_page_request(pid, pn)
                vm_state    = vm_sim.get_state()
                flash_timer = 30 if vm_state["last_fault_frame"] is not None else 0
            step += 1
            if step >= len(sequence):
                status = "Finished"
        except Exception as e:
            error_msg = f"Error: {e}"; status = "Paused"

    def do_reset():
        nonlocal sequence, step, status, flash_timer, scroll, error_msg
        paging_sim.reset(); seg_sim.reset(); vm_sim.reset()
        refresh_states()
        sequence = []; step = 0; flash_timer = 0; scroll = 0
        status = "Ready"; error_msg = ""
        seq_input.clear()

    def do_set_mode(new_mode):
        nonlocal mode
        mode = new_mode; do_reset(); _update_buttons()

    def do_set_algorithm(algo):
        nonlocal algorithm
        algorithm = algo
        paging_sim.set_algorithm(algo)
        seg_sim.set_algorithm(algo)
        vm_sim.set_algorithm(algo)
        _update_buttons()

    while running:
        tick += 1
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False; break

            seq_input.handle_event(event)

            if btn_start.is_clicked(event):  do_start()
            if btn_step.is_clicked(event):   do_step()
            if btn_reset.is_clicked(event):  do_reset()
            if btn_paging.is_clicked(event): do_set_mode("Paging")
            if btn_seg.is_clicked(event):    do_set_mode("Segmentation")
            if btn_vm.is_clicked(event):     do_set_mode("Virtual Memory")
            if btn_fifo.is_clicked(event):   do_set_algorithm("FIFO")
            if btn_lru.is_clicked(event):    do_set_algorithm("LRU")

            if event.type == pygame.MOUSEWHEEL and table_rect.collidepoint(pygame.mouse.get_pos()):
                scroll -= event.y

        if flash_timer > 0:
            flash_timer -= 1

        # ── Render ──────────────────────────────────────────────────────────
        screen.fill(BG_COLOR)

        # Subtle scanline texture
        for sy in range(0, HEIGHT, 4):
            pygame.draw.line(screen, (0, 0, 0), (0, sy), (WIDTH, sy), 1)

        draw_title_bar(screen, step, len(sequence), tick)

        st = active_state()

        # Memory panel
        if mode == "Paging":
            draw_paging_frames(screen, st, flash_timer, mem_rect, paging_frame_anim)
        elif mode == "Segmentation":
            draw_segmentation_frames(screen, st, flash_timer, mem_rect, paging_frame_anim)
        else:
            draw_virtual_frames(screen, st, flash_timer, mem_rect, vm_frame_anim)

        # Page/segment table
        scroll = draw_page_table(screen, st, mode, table_rect, scroll)

        # Sidebar stats
        draw_stats_panel(screen, st, mode, algorithm, status, sidebar_rect,
                         lerp_faults, lerp_swaps, lerp_mem)

        # Controls bar
        draw_controls(screen, ctrl_rect)
        seq_input.draw(screen)
        btn_start.draw(screen); btn_step.draw(screen); btn_reset.draw(screen)
        btn_paging.draw(screen); btn_seg.draw(screen); btn_vm.draw(screen)
        btn_fifo.draw(screen); btn_lru.draw(screen)

        if error_msg:
            draw_error(screen, error_msg, 560, HEIGHT - CTRL_H + 14)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    run()
"""
Paper Bird — a sketchy Flappy Bird clone.
Includes an in-game Settings screen for:
  • Flap key rebinding (any key)
  • Screen resolution selection
  • Game speed
Controls: configured flap key to fly | S for Settings | R to restart
"""

import pygame
import sys
import random
import math
import json
import os

# ── Paper / light-mode palette ─────────────────────────────────────────────────
C_BG        = (245, 240, 228)
C_BG2       = (238, 232, 215)
C_INK       = (45,  35,  20)
C_INK_LIGHT = (90,  75,  55)
C_INK_FAINT = (160, 148, 130)
C_BIRD_FILL = (252, 240, 210)
C_STONE     = (120, 110, 95)
C_GREEN     = (60,  120, 60)
C_HIGHLIGHT = (200, 170, 100)
C_SEL_BG    = (235, 220, 185)
C_BTN_BG    = (230, 222, 205)
C_BTN_HOV   = (215, 200, 170)

# ── Physics ────────────────────────────────────────────────────────────────────
GRAVITY   = 0.45
FLAP_STR  = -8.5
PIPE_W    = 72
GAP       = 165
FPS       = 60

SPEED_LEVELS = {1: 2.0, 2: 3.0, 3: 4.2, 4: 5.5, 5: 7.0}

RESOLUTIONS = [
    (640,  440,  "640 × 440  (Small)"),
    (800,  550,  "800 × 550  (Default)"),
    (1024, 700,  "1024 × 700  (Large)"),
    (1280, 800,  "1280 × 800  (Wide)"),
]

# ── Settings persistence ───────────────────────────────────────────────────────
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "paper_bird_settings.json")

DEFAULT_SETTINGS = {
    "flap_key": pygame.K_UP,
    "resolution_index": 1,   # index into RESOLUTIONS
    "speed_level": 2,
}

def load_settings():
    try:
        with open(SETTINGS_FILE) as f:
            d = json.load(f)
        s = dict(DEFAULT_SETTINGS)
        s.update(d)
        # clamp
        s["resolution_index"] = max(0, min(len(RESOLUTIONS)-1, s["resolution_index"]))
        s["speed_level"]      = max(1, min(5, s["speed_level"]))
        return s
    except Exception:
        return dict(DEFAULT_SETTINGS)

def save_settings(s):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(s, f)
    except Exception:
        pass

# ── Helpers ────────────────────────────────────────────────────────────────────

def jitter(n=2):
    return random.randint(-n, n)

def sketchy_rect(surf, color, rect, lw=2, fill=True, corner_wobble=3):
    x, y, w, h = rect
    pts = [
        (x + jitter(corner_wobble),     y + jitter(corner_wobble)),
        (x + w + jitter(corner_wobble), y + jitter(corner_wobble)),
        (x + w + jitter(corner_wobble), y + h + jitter(corner_wobble)),
        (x + jitter(corner_wobble),     y + h + jitter(corner_wobble)),
    ]
    if fill and color:
        pygame.draw.polygon(surf, color, pts)
    pygame.draw.polygon(surf, C_INK, pts, lw)

def sketchy_circle(surf, fill_color, cx, cy, r, lw=2):
    pygame.draw.circle(surf, fill_color, (cx, cy), r)
    for _ in range(3):
        ox, oy = jitter(1), jitter(1)
        pygame.draw.circle(surf, C_INK, (cx+ox, cy+oy), r+jitter(1), lw)

def draw_hatch(surf, rect, angle=45, gap=10, color=C_INK_LIGHT, alpha=60):
    x, y, w, h = rect
    if w <= 0 or h <= 0:
        return
    clip = pygame.Surface((w, h), pygame.SRCALPHA)
    clip.fill((0,0,0,0))
    r = int(math.hypot(w, h)) + 10
    for d in range(-r, r+w+h, gap):
        if angle == 45:
            pygame.draw.line(clip, (*color, alpha), (d,0), (d-h, h), 1)
        else:
            pygame.draw.line(clip, (*color, alpha), (d,h), (d+h, 0), 1)
    surf.blit(clip, (x, y))

def load_font(size, bold=False):
    for name in ["CourierNew","Courier New","LiberationMono","DejaVuSansMono","FreeMono","monospace"]:
        try:
            f = pygame.font.SysFont(name, size, bold=bold)
            if f:
                return f
        except Exception:
            pass
    return pygame.font.Font(None, size)

def key_name(k):
    """Return a readable name for a pygame key constant."""
    name = pygame.key.name(k)
    return name.upper() if name else f"KEY {k}"

# ── Stone ──────────────────────────────────────────────────────────────────────

class Stone:
    def __init__(self, x, W, H):
        self.W = W
        self.H = H
        self.x      = x
        self.gap_y  = random.randint(110, H - 110 - GAP)
        self.w      = PIPE_W
        self.scored = False
        self._top_cracks = self._make_cracks(self.w, self.gap_y)
        self._bot_cracks = self._make_cracks(self.w, H - self.gap_y - GAP)

    def _make_cracks(self, w, h):
        lines = []
        for _ in range(random.randint(2, 5)):
            sx = random.randint(4, max(5, w-4))
            sy = random.randint(4, max(5, h-4))
            ex = sx + random.randint(-15, 15)
            ey = sy + random.randint(8, 25)
            lines.append(((sx, sy), (ex, min(ey, h-3))))
        return lines

    def update(self, speed):
        self.x -= speed

    def off_screen(self):
        return self.x + self.w < 0

    def get_rects(self):
        top = pygame.Rect(self.x, 0, self.w, self.gap_y)
        bot = pygame.Rect(self.x, self.gap_y + GAP, self.w, self.H - self.gap_y - GAP)
        return top, bot

    def draw(self, surf):
        H = self.H
        top_h = self.gap_y
        bot_y = self.gap_y + GAP
        bot_h = H - bot_y
        cap_h = 14

        self._draw_block(surf, self.x, 0, self.w, top_h, self._top_cracks)
        sketchy_rect(surf, C_STONE, (self.x-4, top_h-cap_h, self.w+8, cap_h), lw=2)
        sketchy_rect(surf, C_STONE, (self.x-4, bot_y, self.w+8, cap_h), lw=2)
        self._draw_block(surf, self.x, bot_y+cap_h, self.w, bot_h-cap_h, self._bot_cracks)

    def _draw_block(self, surf, x, y, w, h, cracks):
        if h <= 0: return
        sketchy_rect(surf, C_STONE, (x, y, w, h), lw=2)
        draw_hatch(surf, (x+2, y+2, w-4, h-4), angle=45, gap=12, alpha=35)
        for (sx,sy),(ex,ey) in cracks:
            pygame.draw.line(surf, C_INK, (x+sx, y+sy), (x+ex, y+ey), 1)
        for i in range(3):
            pygame.draw.line(surf, C_BG, (x+4+i, y+6), (x+4+i, y+min(h-6,30)), 1)

# ── Bird ───────────────────────────────────────────────────────────────────────

class Bird:
    SIZE = 28
    def __init__(self, W, H):
        self.x = int(W * 0.175)
        self.y = H // 2
        self.vy = 0
        self.angle = 0
        self.wing_phase = 0

    def flap(self):
        self.vy = FLAP_STR

    def update(self):
        self.vy += GRAVITY
        self.y  += self.vy
        self.angle = max(-30, min(80, self.vy * 5))
        self.wing_phase += 0.25

    def get_rect(self):
        s = self.SIZE
        return pygame.Rect(self.x - s//2, int(self.y) - s//2, s, s)

    def draw(self, surf):
        cx, cy = self.x, int(self.y)
        r = self.SIZE // 2
        tmp = pygame.Surface((r*2+10, r*2+10), pygame.SRCALPHA)
        tcx, tcy = r+5, r+5

        sketchy_circle(tmp, C_BIRD_FILL, tcx, tcy, r, lw=2)

        wing_off = int(math.sin(self.wing_phase) * 5)
        wing_pts = [(tcx-3, tcy+2),(tcx-r-4, tcy+8+wing_off),(tcx-2, tcy+r-2)]
        pygame.draw.polygon(tmp, C_BIRD_FILL, wing_pts)
        pygame.draw.polygon(tmp, C_INK, wing_pts, 2)

        eye_x, eye_y = tcx+r//2, tcy-4
        pygame.draw.circle(tmp, C_INK, (eye_x, eye_y), 4)
        pygame.draw.circle(tmp, C_BG,  (eye_x+1, eye_y-1), 1)

        beak = [(tcx+r, tcy),(tcx+r+9, tcy+2),(tcx+r, tcy+6)]
        pygame.draw.polygon(tmp, (200,140,60), beak)
        pygame.draw.polygon(tmp, C_INK, beak, 1)

        tail_pts = [(tcx-r+2,tcy-2),(tcx-r-6,tcy-9),(tcx-r-2,tcy+3),(tcx-r-8,tcy+7),(tcx-r+1,tcy+5)]
        pygame.draw.polygon(tmp, C_BIRD_FILL, tail_pts)
        pygame.draw.polygon(tmp, C_INK, tail_pts, 2)

        rotated = pygame.transform.rotate(tmp, -self.angle)
        rr = rotated.get_rect(center=(cx, cy))
        surf.blit(rotated, rr.topleft)

# ── Background ─────────────────────────────────────────────────────────────────

def draw_background(surf, scroll_x, W, H):
    surf.fill(C_BG)
    for row in range(0, H, 32):
        col = C_BG2 if (row//32)%2==0 else C_BG
        pygame.draw.rect(surf, col, (0, row, W, 32))
        pygame.draw.line(surf, (220,212,195), (0,row), (W,row), 1)

    cloud_data = [(150,80,55,28),(370,55,70,32),(600,90,45,22),
                  (100,140,35,18),(500,120,60,26),(720,70,48,24)]
    for bx,by,bw,bh in cloud_data:
        cx = (bx - scroll_x//4) % (W+120) - 60
        for i in range(3):
            r = pygame.Rect(cx+i*(bw//4), by+i*(-bh//6), bw-i*5, bh)
            pygame.draw.ellipse(surf, C_BG, r)
            pygame.draw.ellipse(surf, C_INK_LIGHT, r, 1)
    pygame.draw.line(surf, C_INK, (0,H-2),(W,H-2), 2)

# ── HUD / overlays ─────────────────────────────────────────────────────────────

def draw_score(surf, score, hi, font_big, font_sm, W):
    bx, by, bw, bh = W//2-60, 12, 120, 48
    s = pygame.Surface((bw,bh), pygame.SRCALPHA)
    s.fill((250,245,235,200))
    surf.blit(s,(bx,by))
    sketchy_rect(surf, None, (bx,by,bw,bh), lw=2, fill=False)
    sc = font_big.render(str(score), True, C_INK)
    surf.blit(sc, sc.get_rect(center=(W//2, by+18)))
    hi_t = font_sm.render(f"BEST  {hi}", True, C_INK_LIGHT)
    surf.blit(hi_t, hi_t.get_rect(center=(W//2, by+36)))

def draw_speed_hud(surf, level, font_sm, flap_key):
    kn = key_name(flap_key)
    txt = font_sm.render(
        f"SPEED  {'+'*level}{'-'*(5-level)}  (+/−)    FLAP: {kn}",
        True, C_INK_LIGHT)
    surf.blit(txt, (12,12))

def draw_game_over(surf, score, hi, congrats, font_title, font_med, font_sm, W, H):
    ov = pygame.Surface((W,H), pygame.SRCALPHA)
    ov.fill((245,240,228,210))
    surf.blit(ov,(0,0))

    t = font_title.render("GAME OVER", True, C_INK)
    surf.blit(t, t.get_rect(center=(W//2, H//2-110)))

    s = font_med.render(f"Score: {score}", True, C_INK)
    surf.blit(s, s.get_rect(center=(W//2, H//2-50)))
    b = font_med.render(f"Best:  {hi}",  True, C_INK_LIGHT)
    surf.blit(b, b.get_rect(center=(W//2, H//2-10)))

    if congrats:
        cg = font_med.render("Congratulations!", True, C_GREEN)
        surf.blit(cg, cg.get_rect(center=(W//2, H//2+38)))

    r = font_sm.render("R — restart    S — settings", True, C_INK_LIGHT)
    surf.blit(r, r.get_rect(center=(W//2, H//2+85)))

def draw_start(surf, font_title, font_med, font_sm, settings, W, H):
    ov = pygame.Surface((W,H), pygame.SRCALPHA)
    ov.fill((245,240,228,220))
    surf.blit(ov,(0,0))

    t = font_title.render("PAPER  BIRD", True, C_INK)
    surf.blit(t, t.get_rect(center=(W//2, H//2-130)))

    kn = key_name(settings["flap_key"])
    lines = [
        (f"{kn}  to flap", font_med),
        ("Fly through the stones!", font_sm),
        (f"Speed: {settings['speed_level']}   +/−  to change", font_sm),
        ("S — Settings", font_sm),
        (f"Press  SPACE  or  {kn}  to start", font_med),
    ]
    for i,(txt,fnt) in enumerate(lines):
        s = fnt.render(txt, True, C_INK)
        surf.blit(s, s.get_rect(center=(W//2, H//2-55+i*38)))

# ── Settings Screen ────────────────────────────────────────────────────────────

class SettingsScreen:
    """
    Interactive settings panel drawn entirely in the paper style.
    Sections:
      1. Flap Key  — click [Change] then press any key
      2. Resolution — radio-style list
      3. Speed      — left/right arrows
      4. [Save & Back]  [Cancel]
    """

    SECTION_GAP = 48

    def __init__(self, W, H, fonts, settings):
        self.W = W
        self.H = H
        self.fonts = fonts          # dict: title, med, sm, big
        self.settings = dict(settings)   # working copy
        self.rebinding = False      # waiting for a key press
        self._build_layout()

    def _build_layout(self):
        W, H = self.W, self.H
        cx = W // 2
        y  = int(H * 0.12)

        self.layout = {}

        # ── Flap Key ──
        self.layout["flap_label_y"]  = y
        self.layout["flap_btn"]      = pygame.Rect(cx + 30, y - 16, 250, 34)
        y += self.SECTION_GAP + 10

        # ── Resolution ──
        self.layout["res_label_y"] = y
        y += 30
        self.layout["res_rows"] = []
        for i,(rw,rh,label) in enumerate(RESOLUTIONS):
            row_r = pygame.Rect(cx - 160, y - 2, 450, 30)
            self.layout["res_rows"].append((i, row_r, label))
            y += 34
        y += 10

        # ── Speed ──
        self.layout["speed_label_y"] = y
        self.layout["speed_left"]  = pygame.Rect(cx + 200, y - 1, 30, 30)
        self.layout["speed_right"] = pygame.Rect(cx + 250, y - 1, 30, 30)
        y += self.SECTION_GAP + 10

        # ── Buttons ──
        bw, bh = 300, 40
        self.layout["save_btn"]   = pygame.Rect(cx - bw - 12, y, bw, bh)
        self.layout["cancel_btn"] = pygame.Rect(cx + 12,      y, bw, bh)

    def handle_event(self, ev):
        """Returns 'save', 'cancel', or None."""
        if self.rebinding:
            if ev.type == pygame.KEYDOWN:
                # ESC cancels rebinding without changing key
                if ev.key != pygame.K_ESCAPE:
                    self.settings["flap_key"] = ev.key
                self.rebinding = False
            return None

        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            mp = ev.pos

            # Flap key change button
            if self.layout["flap_btn"].collidepoint(mp):
                self.rebinding = True
                return None

            # Resolution rows
            for i, row_r, _ in self.layout["res_rows"]:
                if row_r.collidepoint(mp):
                    self.settings["resolution_index"] = i
                    return None

            # Speed arrows
            if self.layout["speed_left"].collidepoint(mp):
                self.settings["speed_level"] = max(1, self.settings["speed_level"] - 1)
            if self.layout["speed_right"].collidepoint(mp):
                self.settings["speed_level"] = min(5, self.settings["speed_level"] + 1)

            # Save / Cancel
            if self.layout["save_btn"].collidepoint(mp):
                return "save"
            if self.layout["cancel_btn"].collidepoint(mp):
                return "cancel"

        return None

    def draw(self, surf):
        W, H = self.W, self.H
        fonts = self.fonts
        cx = W // 2

        # Panel background
        panel = pygame.Surface((W, H), pygame.SRCALPHA)
        panel.fill((245,240,228,235))
        surf.blit(panel,(0,0))

        # Title
        t = fonts["title"].render("SETTINGS", True, C_INK)
        surf.blit(t, t.get_rect(center=(cx, int(H*0.06))))

        # ── Flap Key section ──
        ly = self.layout["flap_label_y"]
        label = fonts["med"].render("Flap Key", True, C_INK)
        surf.blit(label, (cx - 450, ly - 10))

        btn_r = self.layout["flap_btn"]
        btn_color = C_HIGHLIGHT if self.rebinding else C_BTN_BG
        pygame.draw.rect(surf, btn_color, btn_r, border_radius=4)
        sketchy_rect(surf, None, btn_r, lw=2, fill=False, corner_wobble=2)

        if self.rebinding:
            btn_txt = fonts["sm"].render("Press any key…", True, C_INK)
        else:
            kn = key_name(self.settings["flap_key"])
            btn_txt = fonts["sm"].render(f"[ {kn} ]  Change", True, C_INK)
        surf.blit(btn_txt, btn_txt.get_rect(center=btn_r.center))

        # Divider
        self._divider(surf, ly + 28)

        # ── Resolution section ──
        ry = self.layout["res_label_y"]
        rl = fonts["med"].render("Resolution", True, C_INK)
        surf.blit(rl, (cx - 450, ry - 1))

        sel = self.settings["resolution_index"]
        for i, row_r, label in self.layout["res_rows"]:
            bg = C_SEL_BG if i == sel else C_BTN_BG
            hover = row_r.collidepoint(pygame.mouse.get_pos())
            if hover and i != sel:
                bg = C_BTN_HOV
            pygame.draw.rect(surf, bg, row_r, border_radius=3)
            if i == sel:
                pygame.draw.rect(surf, C_HIGHLIGHT, row_r, 2, border_radius=3)
            else:
                pygame.draw.rect(surf, C_INK_FAINT, row_r, 1, border_radius=3)

            mark = "●" if i == sel else "○"
            row_txt = fonts["sm"].render(f"  {mark}  {label}", True, C_INK if i==sel else C_INK_LIGHT)
            surf.blit(row_txt, row_txt.get_rect(midleft=(row_r.x+10, row_r.centery)))

        # Divider after last res row
        last_row = self.layout["res_rows"][-1][1]
        self._divider(surf, last_row.bottom + 10)

        # ── Speed section ──
        sy = self.layout["speed_label_y"]
        sl = fonts["med"].render("Game Speed", True, C_INK)
        surf.blit(sl, (cx - 450, sy - 1))

        lvl = self.settings["speed_level"]
        bar_txt = fonts["med"].render(f"{'+'*lvl}{'-'*(5-lvl)}  {lvl}/5", True, C_INK)
        surf.blit(bar_txt, bar_txt.get_rect(center=(cx, sy+14)))

        for btn_r, ch in [(self.layout["speed_left"],"◀"), (self.layout["speed_right"],"▶")]:
            hover = btn_r.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(surf, C_BTN_HOV if hover else C_BTN_BG, btn_r, border_radius=4)
            sketchy_rect(surf, None, btn_r, lw=2, fill=False, corner_wobble=2)
            ct = fonts["med"].render(ch, True, C_INK)
            surf.blit(ct, ct.get_rect(center=btn_r.center))

        self._divider(surf, sy + 36)

        # ── Save / Cancel buttons ──
        for btn_r, label, primary in [
            (self.layout["save_btn"],   "Save & Back", True),
            (self.layout["cancel_btn"], "Cancel",      False),
        ]:
            hover = btn_r.collidepoint(pygame.mouse.get_pos())
            bg = C_SEL_BG if (hover and primary) else (C_BTN_HOV if hover else C_BTN_BG)
            pygame.draw.rect(surf, bg, btn_r, border_radius=5)
            sketchy_rect(surf, None, btn_r, lw=2, fill=False, corner_wobble=2)
            bt = fonts["med"].render(label, True, C_INK)
            surf.blit(bt, bt.get_rect(center=btn_r.center))

        # Hint at bottom
        hint = fonts["sm"].render("ESC cancels key rebinding", True, C_INK_FAINT)
        surf.blit(hint, hint.get_rect(center=(cx, H - 22)))

    def _divider(self, surf, y):
        x0, x1 = int(self.W * 0.15), int(self.W * 0.85)
        for dy in range(2):
            pygame.draw.line(surf, C_INK_FAINT if dy else C_INK_LIGHT,
                             (x0+jitter(2), y+dy), (x1+jitter(2), y+dy), 1)

# ── Main ───────────────────────────────────────────────────────────────────────

def make_screen(res_index):
    W, H, _ = RESOLUTIONS[res_index]
    return pygame.display.set_mode((W, H)), W, H

def main():
    pygame.init()
    pygame.display.set_caption("Paper Bird")
    clock = pygame.time.Clock()

    settings = load_settings()

    screen, W, H = make_screen(settings["resolution_index"])

    def make_fonts(H):
        scale = H / 550
        return {
            "title": load_font(int(58*scale), bold=True),
            "med":   load_font(int(28*scale), bold=True),
            "big":   load_font(int(34*scale), bold=True),
            "sm":    load_font(int(18*scale)),
        }

    fonts = make_fonts(H)
    hi_score = 0

    def new_game():
        bird   = Bird(W, H)
        stones = [Stone(W+100, W, H), Stone(W+100+W//2+20, W, H)]
        return bird, stones, 0, 0

    bird, stones, score, scroll_x = new_game()
    state    = "start"
    congrats = False
    settings_screen = None

    while True:
        clock.tick(FPS)
        speed = SPEED_LEVELS[settings["speed_level"]]
        flap_key = settings["flap_key"]

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                save_settings(settings)
                pygame.quit(); sys.exit()

            # ── Settings state ──
            if state == "settings" and settings_screen:
                result = settings_screen.handle_event(ev)
                if result == "save":
                    new_res = settings_screen.settings["resolution_index"]
                    need_resize = new_res != settings["resolution_index"]
                    settings.update(settings_screen.settings)
                    save_settings(settings)
                    if need_resize:
                        screen, W, H = make_screen(settings["resolution_index"])
                        fonts = make_fonts(H)
                        bird, stones, score, scroll_x = new_game()
                        congrats = False
                    state = settings_screen._prev_state
                    settings_screen = None
                elif result == "cancel":
                    state = settings_screen._prev_state
                    settings_screen = None
                continue

            # ── Global speed keys (not in settings) ──
            if ev.type == pygame.KEYDOWN and state != "settings":
                if ev.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    settings["speed_level"] = min(5, settings["speed_level"]+1)
                if ev.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    settings["speed_level"] = max(1, settings["speed_level"]-1)
                if ev.key == pygame.K_s:
                    settings_screen = SettingsScreen(W, H, fonts, settings)
                    settings_screen._prev_state = state
                    state = "settings"
                    continue

            if state == "start":
                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_SPACE, flap_key):
                        state = "playing"
                        bird.flap()

            elif state == "playing":
                if ev.type == pygame.KEYDOWN:
                    if ev.key == flap_key:
                        bird.flap()

            elif state == "dead":
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_r:
                        bird, stones, score, scroll_x = new_game()
                        state = "playing"
                        congrats = False

        # ── Update ──
        if state == "playing":
            scroll_x += speed
            bird.update()
            for st in stones:
                st.update(speed)
            for i, st in enumerate(stones):
                if st.off_screen():
                    other = stones[1-i]
                    stones[i] = Stone(other.x + W//2 + 20 + random.randint(-20,20), W, H)
            for st in stones:
                if not st.scored and st.x + st.w < bird.x:
                    st.scored = True
                    score += 1
            bird_rect = bird.get_rect()
            hit = any(bird_rect.colliderect(r) for st in stones for r in st.get_rects())
            if bird.y > H or bird.y < 0:
                hit = True
            if hit:
                congrats = score > hi_score
                if score > hi_score:
                    hi_score = score
                state = "dead"

        # ── Draw ──
        draw_background(screen, int(scroll_x), W, H)
        for st in stones:
            st.draw(screen)
        if state not in ("start",):
            bird.draw(screen)

        if state == "playing":
            draw_score(screen, score, hi_score, fonts["big"], fonts["sm"], W)
            draw_speed_hud(screen, settings["speed_level"], fonts["sm"], flap_key)

        elif state == "start":
            draw_start(screen, fonts["title"], fonts["med"], fonts["sm"], settings, W, H)

        elif state == "dead":
            draw_score(screen, score, hi_score, fonts["big"], fonts["sm"], W)
            draw_speed_hud(screen, settings["speed_level"], fonts["sm"], flap_key)
            draw_game_over(screen, score, hi_score, congrats,
                           fonts["title"], fonts["med"], fonts["sm"], W, H)

        elif state == "settings" and settings_screen:
            settings_screen.draw(screen)

        pygame.display.flip()

if __name__ == "__main__":
    main()
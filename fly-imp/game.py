"""2D fly dodgeball viewer (pygame).

    python game.py                 # play / watch
    python game.py --seed 3        # different ball sequence

Keys:  L lesion the Giant Fibre   1 fly brain   2 dumb distance rule   3 never dodges
       R reset   SPACE pause   +/- ball rate   click: throw a ball at the fly   ESC quit
"""
import argparse
import math

import numpy as np
import pygame

from sim import ARENA_H, ARENA_W, FLY_R, World

S = 60                      # pixels per world unit
HUD_H = 84
ARENA_PX = (int(ARENA_W * S), int(ARENA_H * S))
WIN = (ARENA_PX[0], ARENA_PX[1] + HUD_H)
BALL_COLORS = [(231, 76, 60), (52, 152, 219), (241, 196, 15), (46, 204, 113), (155, 89, 182), (230, 126, 34)]


def px(p):
    return int(p[0] * S), int((ARENA_H - p[1]) * S)


def draw_floor(surf):
    surf.fill((34, 38, 46), (0, 0, *ARENA_PX))
    for gx in range(0, int(ARENA_W) + 1):
        pygame.draw.line(surf, (44, 49, 59), (gx * S, 0), (gx * S, ARENA_PX[1]))
    for gy in range(0, int(ARENA_H) + 1):
        pygame.draw.line(surf, (44, 49, 59), (0, gy * S), (ARENA_PX[0], gy * S))
    pygame.draw.rect(surf, (90, 98, 112), (0, 0, *ARENA_PX), 3)


def draw_ball(surf, b, idx):
    c = px(b.pos)
    rad = max(3, int(b.r * S))
    col = BALL_COLORS[idx % len(BALL_COLORS)]
    pygame.draw.circle(surf, (20, 22, 27), (c[0] + 4, c[1] + 5), rad)           # shadow
    pygame.draw.circle(surf, col, c, rad)
    pygame.draw.circle(surf, (255, 255, 255), c, rad, 2)
    a = -b.angle                                                                # rolling stripe
    pygame.draw.line(surf, (255, 255, 255), c, (c[0] + rad * math.cos(a), c[1] + rad * math.sin(a)), 3)


def ellipse_pts(P, cx, cy, ax, ay, n=18):
    return [P(cx + ax * math.cos(2 * math.pi * k / n), cy + ay * math.sin(2 * math.pi * k / n)) for k in range(n)]


def draw_fly(surf, overlay, w):
    f = np.array([math.cos(w.heading), math.sin(w.heading)])
    left = np.array([-f[1], f[0]])
    P = lambda fx, ly: px(w.pos + f * fx + left * ly)          # local (forward, left) -> screen
    flap = 0.8 + 0.2 * math.sin(w.t * 70)
    for side in (1, -1):                                       # wings (translucent)
        wing = [P(0.02, side * 0.08), P(-0.10, side * 0.5 * flap), P(-0.55, side * 0.42 * flap),
                P(-0.62, side * 0.15), P(-0.2, side * 0.06)]
        pygame.draw.polygon(overlay, (200, 225, 255, 105), wing)
        pygame.draw.polygon(overlay, (230, 240, 255, 190), wing, 1)
    for i, fx in enumerate((0.12, 0.02, -0.08)):               # legs
        for side in (1, -1):
            pygame.draw.line(surf, (25, 20, 15), P(fx, side * 0.1), P(fx + 0.12 * (1 - i), side * 0.34), 2)
    pygame.draw.polygon(surf, (105, 76, 48), ellipse_pts(P, -0.24, 0, 0.27, 0.15))   # abdomen
    for sx in (-0.15, -0.26, -0.37):
        pygame.draw.line(surf, (60, 42, 26), P(sx, -0.13), P(sx, 0.13), 2)
    pygame.draw.polygon(surf, (78, 56, 36), ellipse_pts(P, 0.02, 0, 0.16, 0.13))     # thorax
    pygame.draw.polygon(surf, (70, 50, 32), ellipse_pts(P, 0.2, 0, 0.1, 0.1))        # head
    for side, hz in ((1, w.hz_l), (-1, w.hz_r)):                                     # eyes glow with looming drive
        k = min(hz / 200.0, 1.0)
        col = (int(120 + 135 * k), int(20 + 110 * k), int(20 + 20 * k))
        pygame.draw.circle(surf, col, P(0.23, side * 0.09), max(3, int(0.075 * S)))
    if w.cooldown > 0.2:
        pygame.draw.circle(surf, (255, 255, 255), px(w.pos), int(FLY_R * S * 2.2), 2)


def draw_effects(surf, effects, t):
    for kind, pos, t0 in effects:
        age = t - t0
        col = (255, 70, 70) if kind == "hit" else (230, 230, 255)
        r = int((0.3 + age * 2.5) * S)
        pygame.draw.circle(surf, col, px(pos), r, 3)


def draw_hud(surf, w, font, small, paused):
    y0 = ARENA_PX[1]
    surf.fill((20, 22, 28), (0, y0, WIN[0], HUD_H))
    brain = "REAL connectome table" if w.brain.real else "PLACEHOLDER table (run build_table.py)"
    pol = {"fly": "fly brain", "dumb": "dumb distance rule", "none": "never dodges"}[w.policy]
    lesion = "  [GIANT FIBRE LESIONED]" if (w.lesion and w.policy == "fly") else ""
    surf.blit(font.render(f"{pol}{lesion}   |   {brain}{'   |   PAUSED' if paused else ''}", True, (235, 235, 240)), (12, y0 + 6))
    s = w.stats
    surf.blit(font.render(f"hits {s['hits']}    dodged {s['dodged']}    close calls {s['close']}    jumps {s['jumps']}    t={w.t:.0f}s",
                          True, (140, 220, 160)), (12, y0 + 30))
    for i, (name, hz) in enumerate((("L eye", w.hz_l), ("R eye", w.hz_r))):
        x = 560 + i * 200
        surf.blit(small.render(f"{name} looming {hz:3.0f} Hz", True, (200, 200, 210)), (x, y0 + 8))
        pygame.draw.rect(surf, (60, 64, 74), (x, y0 + 28, 180, 10))
        pygame.draw.rect(surf, (255, 150, 60), (x, y0 + 28, int(180 * hz / 200), 10))
    o = w.last_out
    surf.blit(small.render(f"Giant Fibre {o['gf']:5.0f} Hz     MDN {o['mdn']:4.0f} Hz", True, (200, 200, 210)), (560, y0 + 46))
    surf.blit(small.render("L lesion   1 fly   2 dumb   3 none   R reset   SPACE pause   +/- ball rate   click: throw a ball",
                           True, (130, 135, 150)), (12, y0 + 62))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--frames", type=int, default=0, help="headless test: run N fixed frames then exit")
    ap.add_argument("--shot", default="", help="with --frames: save a screenshot at the end")
    args = ap.parse_args()

    pygame.init()
    screen = pygame.display.set_mode(WIN)
    pygame.display.set_caption("Fly dodgeball")
    font, small = pygame.font.Font(None, 26), pygame.font.Font(None, 22)
    overlay = pygame.Surface(ARENA_PX, pygame.SRCALPHA)
    clock = pygame.time.Clock()
    w = World(seed=args.seed)
    effects, paused, acc, DT, frame = [], False, 0.0, 1 / 120, 0

    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_l:
                    w.lesion = not w.lesion
                elif e.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    w.policy = {pygame.K_1: "fly", pygame.K_2: "dumb", pygame.K_3: "none"}[e.key]
                    w.reset(); effects.clear()
                elif e.key == pygame.K_r:
                    w.reset(); effects.clear()
                elif e.key == pygame.K_SPACE:
                    paused = not paused
                elif e.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    w.spawn_every = max(0.2, w.spawn_every * 0.8)
                elif e.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    w.spawn_every = min(6.0, w.spawn_every * 1.25)
            elif e.type == pygame.MOUSEBUTTONDOWN and e.pos[1] < ARENA_PX[1]:
                w.spawn_at(np.array([e.pos[0] / S, ARENA_H - e.pos[1] / S]))

        if args.frames:
            ticks = 2                                  # deterministic: 2 x 1/120 s per frame
            frame += 1
            if frame >= args.frames:
                running = False
        else:
            acc += min(clock.tick(60) / 1000.0, 0.05)
            ticks = 0
            while acc >= DT:
                acc -= DT; ticks += 1
        if not paused:
            for _ in range(ticks):
                w.step(DT)
        for kind, pos in w.events:
            effects.append((kind, pos, w.t))
        w.events.clear()
        effects = [x for x in effects if w.t - x[2] < 0.5]

        draw_floor(screen)
        overlay.fill((0, 0, 0, 0))
        for i, b in enumerate(w.balls):
            draw_ball(screen, b, i)
        draw_fly(screen, overlay, w)
        screen.blit(overlay, (0, 0))
        draw_effects(screen, effects, w.t)
        draw_hud(screen, w, font, small, paused)
        pygame.display.flip()

    if args.shot:
        pygame.image.save(screen, args.shot)
    pygame.quit()


if __name__ == "__main__":
    main()

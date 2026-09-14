#!/usr/bin/env python3
"""Helix Aegis — neon rotating-shield arcade for ElbowOS. Python 3 + pygame."""
import math, os, random, subprocess, sys

RECORD = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
PLAY = "--play" in sys.argv
if RECORD or not PLAY:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

W, H, FPS, SECS = 1080, 1920, 30, 15
OUT = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/HELIX_AEGIS_ElbowOS.mp4")
TITLE, HANDLE = "HELIX AEGIS", "x.com/ElbowOS"

BG = (8, 4, 18)
INK = (28, 10, 48)
GOLD = (255, 214, 70)
WHITE = (244, 240, 255)
CYAN = (40, 255, 220)
MAG = (255, 60, 170)
LIME = (190, 255, 80)
AMBER = (255, 140, 40)
ROSE = (255, 90, 120)
TEAL = (30, 210, 255)


class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        flags = 0 if PLAY else pygame.HIDDEN
        try:
            self.screen = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            pygame.display.quit()
            pygame.display.init()
            self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(TITLE)
        self.font_lg = pygame.font.SysFont("DejaVu Sans", 62, bold=True)
        self.font = pygame.font.SysFont("DejaVu Sans", 40, bold=True)
        self.font_sm = pygame.font.SysFont("DejaVu Sans", 26)
        self.clock = pygame.time.Clock()
        self.cx, self.cy = W // 2, 980
        self.core_r, self.shield_r = 54, 168
        self.arc = math.radians(62)
        self.ang = -math.pi / 2
        self.omega = 0.0
        self.score = self.combo = self.t = self.flash = self.lives = 0
        self.shards, self.sparks, self.rings, self.stars = [], [], [], []
        for _ in range(70):
            self.stars.append([
                random.randint(0, W), random.randint(0, H),
                random.uniform(0.4, 2.2), random.choice([CYAN, MAG, GOLD, LIME, TEAL])
            ])
        self.reset()

    def reset(self):
        self.shards.clear()
        self.lives = 3
        self.combo = 0
        self.ang = -math.pi / 2
        self.omega = 0.0
        self.spawn_cd = 8

    def burst(self, x, y, col, n=10):
        for _ in range(n):
            a = random.uniform(0, 6.2832)
            sp = random.uniform(2.2, 12)
            self.sparks.append([x, y, math.cos(a) * sp, math.sin(a) * sp, 20, col])

    def spawn_shard(self):
        side = random.choice(("t", "b", "l", "r"))
        if side == "t":
            x, y = random.uniform(80, W - 80), -30
        elif side == "b":
            x, y = random.uniform(80, W - 80), H + 30
        elif side == "l":
            x, y = -30, random.uniform(220, H - 220)
        else:
            x, y = W + 30, random.uniform(220, H - 220)
        dx, dy = self.cx - x, self.cy - y
        dist = math.hypot(dx, dy) or 1
        spd = random.uniform(5.2, 9.4) + min(4.0, self.t / 90)
        col = random.choice([MAG, ROSE, TEAL, CYAN, LIME])
        self.shards.append([x, y, dx / dist * spd, dy / dist * spd, 18, col])

    def wrap_delta(self, a, b):
        d = (b - a + math.pi) % (2 * math.pi) - math.pi
        return d

    def autoplay(self):
        if not self.shards:
            self.omega *= 0.7
            return
        best, best_t = None, 1e9
        for s in self.shards:
            vx, vy = s[2], s[3]
            relx, rely = s[0] - self.cx, s[1] - self.cy
            inward = -(relx * vx + rely * vy)
            if inward <= 0:
                continue
            r = math.hypot(relx, rely)
            eta = max(0.1, (r - self.shield_r) / (inward / (r or 1) + 0.01))
            if eta < best_t:
                best_t, best = eta, s
        target = best or self.shards[0]
        want = math.atan2(target[1] - self.cy, target[0] - self.cx)
        err = self.wrap_delta(self.ang, want)
        self.omega = max(-0.18, min(0.18, err * 0.28))

    def collide(self):
        keep = []
        for s in self.shards:
            dx, dy = s[0] - self.cx, s[1] - self.cy
            r = math.hypot(dx, dy)
            if r < self.core_r + 8:
                self.lives -= 1
                self.combo = 0
                self.flash = 10
                self.burst(s[0], s[1], ROSE, 18)
                self.rings.append([self.cx, self.cy, 20, ROSE])
                if self.lives <= 0:
                    self.score = max(0, self.score - 40)
                    self.reset()
                continue
            if abs(r - self.shield_r) < 22:
                a = math.atan2(dy, dx)
                if abs(self.wrap_delta(self.ang, a)) < self.arc * 0.55:
                    self.combo += 1
                    self.score += 20 + self.combo * 4
                    self.burst(s[0], s[1], GOLD, 14)
                    self.rings.append([s[0], s[1], 8, s[5]])
                    continue
            keep.append(s)
        self.shards = keep

    def tick(self):
        self.t += 1
        self.flash = max(0, self.flash - 1)
        self.ang = (self.ang + self.omega) % (2 * math.pi)
        self.omega *= 0.92
        self.spawn_cd -= 1
        if self.spawn_cd <= 0:
            self.spawn_shard()
            if random.random() < 0.35:
                self.spawn_shard()
            self.spawn_cd = max(10, 22 - self.t // 40)
        for s in self.shards:
            s[0] += s[2]
            s[1] += s[3]
        self.collide()
        for p in self.sparks:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.12
            p[4] -= 1
        self.sparks = [p for p in self.sparks if p[4] > 0]
        for r in self.rings:
            r[2] += 7
        self.rings = [r for r in self.rings if r[2] < 160]
        for e in self.stars:
            e[1] -= e[2]
            if e[1] < -6:
                e[1] = H + 6
                e[0] = random.randint(0, W)

    def draw_shield(self, surf):
        steps = 18
        pts_outer, pts_inner = [], []
        half = self.arc / 2
        for i in range(steps + 1):
            a = self.ang - half + self.arc * i / steps
            pts_outer.append((self.cx + math.cos(a) * (self.shield_r + 16),
                              self.cy + math.sin(a) * (self.shield_r + 16)))
            pts_inner.append((self.cx + math.cos(a) * (self.shield_r - 16),
                              self.cy + math.sin(a) * (self.shield_r - 16)))
        poly = pts_outer + list(reversed(pts_inner))
        pygame.draw.polygon(surf, GOLD, poly)
        pygame.draw.polygon(surf, WHITE, poly, 3)
        tip = (self.cx + math.cos(self.ang) * (self.shield_r + 28),
               self.cy + math.sin(self.ang) * (self.shield_r + 28))
        pygame.draw.circle(surf, LIME, (int(tip[0]), int(tip[1])), 10)

    def draw(self, surf):
        surf.fill(BG)
        for e in self.stars:
            pygame.draw.circle(surf, e[3], (int(e[0]), int(e[1])), 2)
        pulse = 8 + int(6 * math.sin(self.t * 0.11))
        pygame.draw.circle(surf, INK, (self.cx, self.cy), self.shield_r + 80)
        pygame.draw.circle(surf, (40, 16, 70), (self.cx, self.cy), self.shield_r + 78, 2)
        pygame.draw.circle(surf, (70, 30, 110), (self.cx, self.cy), self.shield_r, 2)
        pygame.draw.circle(surf, AMBER, (self.cx, self.cy), self.core_r + pulse // 2)
        pygame.draw.circle(surf, GOLD, (self.cx, self.cy), self.core_r - 8)
        pygame.draw.circle(surf, WHITE, (self.cx - 12, self.cy - 14), 10)
        self.draw_shield(surf)
        for s in self.shards:
            pygame.draw.circle(surf, s[5], (int(s[0]), int(s[1])), int(s[4]))
            pygame.draw.circle(surf, WHITE, (int(s[0] - 4), int(s[1] - 4)), 4)
        for r in self.rings:
            pygame.draw.circle(surf, r[3], (int(r[0]), int(r[1])), int(r[2]), 3)
        for p in self.sparks:
            pygame.draw.circle(surf, p[5], (int(p[0]), int(p[1])), max(2, p[4] // 4))
        if self.flash:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((255, 70, 130, 40))
            surf.blit(ov, (0, 0))
        title = self.font_lg.render(TITLE, True, CYAN)
        surf.blit(title, title.get_rect(center=(W // 2, 86)))
        sub = self.font_sm.render(HANDLE, True, MAG)
        surf.blit(sub, sub.get_rect(center=(W // 2, 148)))
        sc = self.font.render(f"SCORE  {self.score}", True, WHITE)
        lv = self.font.render(f"AEGIS  {'◆' * self.lives}", True, GOLD)
        cb = self.font_sm.render(f"COMBO  x{self.combo}", True, LIME)
        surf.blit(sc, sc.get_rect(center=(W // 2, H - 168)))
        surf.blit(lv, lv.get_rect(center=(W // 2, H - 108)))
        surf.blit(cb, cb.get_rect(center=(W // 2, H - 58)))

    def play_interactive(self):
        running = True
        while running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    running = False
                elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_r:
                    self.reset()
                    self.score = 0
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.omega = -0.14
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.omega = 0.14
            self.tick()
            self.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()

    def record(self):
        frames = FPS * SECS
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart",
            OUT,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        canvas = pygame.Surface((W, H))
        try:
            for i in range(frames):
                self.autoplay()
                self.tick()
                self.draw(canvas)
                proc.stdin.write(pygame.image.tostring(canvas, "RGB"))
                if i % 30 == 0:
                    print(f"frame {i}/{frames}", flush=True)
        finally:
            proc.stdin.close()
            err = proc.stderr.read().decode("utf-8", "ignore")
            rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed ({rc}):\n{err[-1200:]}")
        print("wrote", OUT)
        pygame.quit()


def main():
    g = Game()
    if PLAY and not RECORD:
        g.play_interactive()
    else:
        g.record()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Draw the front page 'MONDAY 23 NOVEMBER 2026' of a broadsheet summing up
one day of world news, entirely from code, and save it as entry.png
(1024x1024) beside this script.

Every mark -- type, rules, chips, pictograms -- is drawn with Pillow
primitives; no image is loaded.  No network, no clock, no randomness, so the
same source gives the same bytes on every run.

Layout, top to bottom:
    8px ink bar, kicker line, 3px rule
    the date in 62px serif, 3px rule
    strap line + legend, hairline
    3 lead columns (chip, small picture, 21/24px headline, 13px standfirst),
    closed by a 2px rule
    3 x 4 grid of stories, hairlines between rows
    40px ink footer
"""
import os

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- palette
W = H = 1024
PAPER = (250, 248, 244)
INK = (17, 20, 24)
MUTED = (92, 99, 107)
RULE = (176, 182, 189)
RED = (176, 30, 30)

FD = "/usr/share/fonts/truetype/dejavu/"
img = Image.new("RGB", (W, H), PAPER)
d = ImageDraw.Draw(img)


def F(name, size):
    return ImageFont.truetype(FD + name, size)


SERIF = F("DejaVuSerif-Bold.ttf", 62)
B24 = F("DejaVuSans-Bold.ttf", 24)
B21 = F("DejaVuSans-Bold.ttf", 21)
B20 = F("DejaVuSans-Bold.ttf", 20)
B19 = F("DejaVuSans-Bold.ttf", 19)
B23 = F("DejaVuSans-Bold.ttf", 23)
B16 = F("DejaVuSans-Bold.ttf", 16)
B15 = F("DejaVuSans-Bold.ttf", 15)
B12 = F("DejaVuSans-Bold.ttf", 12)
B10 = F("DejaVuSans-Bold.ttf", 10)
R13 = F("DejaVuSans.ttf", 13)
R11 = F("DejaVuSans.ttf", 11)

ASC, DESC = R13.getmetrics()


# ---------------------------------------------------------------- helpers
def tw(text, font):
    return d.textlength(text, font=font)


def line_width(words, font):
    if not words:
        return 0.0
    return sum(tw(w, font) for w in words) + tw(" ", font) * (len(words) - 1)


def wrap(text, font, maxw):
    """Balanced wrap.  For each possible line count, pick the break points that
    minimise the sum of squared slack, so no line is a stub and no word ever
    leaves the column.  Returns the fewest lines that still look even."""
    words = text.split()
    if len(words) == 1:
        return [text]
    wid = [tw(w, font) for w in words]
    space = tw(" ", font)
    n = len(words)
    # width[i][j] = width of words i..j on one line, inf if it does not fit
    INF = float("inf")
    width = [[INF] * n for _ in range(n)]
    for i in range(n):
        w = 0.0
        for j in range(i, n):
            w += wid[j] + (space if j > i else 0.0)
            if w > maxw:
                break
            width[i][j] = w

    best = None
    for nlines in range(1, n + 1):
        # cost[k][i] = best cost breaking words k..n-1 into i lines
        cost = [[INF] * (nlines + 1) for _ in range(n + 1)]
        back = [[-1] * (nlines + 1) for _ in range(n + 1)]
        cost[n][0] = 0.0
        for i in range(n - 1, -1, -1):
            for lines in range(1, nlines + 1):
                for j in range(i, n):
                    if width[i][j] == INF or cost[j + 1][lines - 1] == INF:
                        continue
                    slack = maxw - width[i][j]
                    # the last line is allowed to be short (ragged right); the
                    # earlier lines are not, so headlines fall long-to-short
                    weight = 0.5 if j == n - 1 else 1.0
                    c = cost[j + 1][lines - 1] + weight * slack * slack
                    if c < cost[i][lines]:
                        cost[i][lines] = c
                        back[i][lines] = j
        if cost[0][nlines] == INF:
            continue
        lines, i, k = [], 0, nlines
        while k:
            j = back[i][k]
            lines.append(" ".join(words[i:j + 1]))
            i, k = j + 1, k - 1
        if best is None:
            best = lines
            if tw(lines[-1], font) >= 0.50 * maxw:
                return lines           # fewest lines, and the last one is full
            continue                   # else try one more line for balance
        return best                    # one extra line did not help: keep it
    return best


LAYOUT = []                         # (x0, y0, x1, y1, label) of drawn text
GLYPH_BOXES = []                    # (kind, x0, y0, x1, y1) of drawn pictograms


def block(x, y, maxw, text, font, lh, colour=INK):
    """Draw wrapped text inside maxw; assert it fits; record its box."""
    lines = wrap(text, font, maxw)
    for i, ln in enumerate(lines):
        assert tw(ln, font) <= maxw + 0.5, (ln, tw(ln, font), maxw)
        assert x + tw(ln, font) <= RIGHT, (ln, "runs off the page")
        d.text((x, y + i * lh), ln, font=font, fill=colour)
        bb = d.textbbox((x, y + i * lh), ln, font=font)
        LAYOUT.append((bb[0], bb[1], bb[2], bb[3], ln))
    return y + len(lines) * lh


def line(x, y, text, font, colour=INK):
    """One unwrapped line: assert it fits on the page, record its box."""
    w = tw(text, font)
    assert x + w <= RIGHT + 1 and x >= LEFT - 8, (text, x, w)
    d.text((x, y), text, font=font, fill=colour)
    bb = d.textbbox((x, y), text, font=font)
    LAYOUT.append((bb[0], bb[1], bb[2], bb[3], text))
    return x + w


def chip(x, y, label, colour=INK):
    """Filled region label; returns x just after it."""
    w = tw(label, B10)
    d.rectangle([x, y, x + w + 10, y + 15], fill=colour)
    d.text((x + 5, y + 2.5), label, font=B10, fill=(255, 255, 255))
    return x + w + 10


# ---------------------------------------------------------------- pictograms


def glyph(kind, x, y, s, col=INK):
    """Pictograms drawn from rectangles, ellipses, lines, arcs and polygons.
    The box is s x s at (x, y); callers keep text out of it."""
    GLYPH_BOXES.append((kind, x, y, x + s, y + s))
    m = s / 2.0
    cx, cy = x + m, y + m
    lw = max(2, round(s / 12))
    lw2 = max(1, round(s / 22))

    if kind == "radar":                       # dish, arcs, and a target blip
        d.arc([x + 0.04 * s, y + 0.10 * s, x + 0.86 * s, y + 0.86 * s], 200, 340,
              fill=col, width=lw)
        d.arc([x + 0.20 * s, y + 0.26 * s, x + 0.70 * s, y + 0.70 * s], 200, 340,
              fill=col, width=lw2)
        d.polygon([(x + 0.44 * s, y + 0.20 * s), (x + 0.86 * s, y + 0.02 * s),
                   (x + 0.86 * s, y + 0.22 * s)], fill=col)
        d.ellipse([cx - 0.07 * s, y + 0.62 * s, cx + 0.07 * s, y + 0.76 * s], fill=RED)
        for k in range(2):
            xx = x + (0.16 + 0.20 * k) * s
            d.line([xx, y + 0.88 * s, xx, y + 0.99 * s], fill=col, width=lw2)

    elif kind == "globe":                     # globe with meridians
        d.ellipse([x + 1.5, y + 1.5, x + s - 1.5, y + s - 1.5], outline=col, width=lw)
        d.ellipse([cx - 0.24 * s, y + 1.5, cx + 0.24 * s, y + s - 1.5], outline=col, width=lw2)
        d.line([x + 2.5, cy, x + s - 2.5, cy], fill=col, width=lw2)

    elif kind == "chart":                     # bars falling, arrow down-right
        for i, top in enumerate((0.06, 0.24, 0.42, 0.60)):
            bx = x + 0.04 * s + i * 0.165 * s
            d.rectangle([bx, y + top * s, bx + 0.12 * s, y + 0.96 * s], fill=col)
        d.line([x + 0.06 * s, y + 0.10 * s, x + 0.60 * s, y + 0.46 * s], fill=RED, width=lw)
        d.line([x + 0.60 * s, y + 0.46 * s, x + 0.94 * s, y + 0.70 * s], fill=RED, width=lw)
        d.polygon([(x + 0.94 * s, y + 0.70 * s), (x + 0.66 * s, y + 0.64 * s),
                   (x + 0.86 * s, y + 0.50 * s)], fill=RED)

    elif kind == "ship":                      # warship: low hull, bridge, mast
        d.polygon([(x + 0.02 * s, y + 0.62 * s), (x + 0.98 * s, y + 0.62 * s),
                   (x + 0.86 * s, y + 0.78 * s), (x + 0.12 * s, y + 0.78 * s)], fill=col)
        d.rectangle([x + 0.50 * s, y + 0.46 * s, x + 0.72 * s, y + 0.62 * s], fill=col)
        d.rectangle([x + 0.56 * s, y + 0.34 * s, x + 0.66 * s, y + 0.46 * s], fill=col)
        d.line([x + 0.20 * s, y + 0.62 * s, x + 0.20 * s, y + 0.36 * s], fill=col, width=lw2)
        d.rectangle([x + 0.24 * s, y + 0.36 * s, x + 0.38 * s, y + 0.44 * s], fill=col)
        for k in range(2):
            yy = y + 0.86 * s + k * 0.10 * s
            d.arc([x, yy - 0.06 * s, x + 0.30 * s, yy + 0.06 * s], 0, 160, fill=col, width=lw2)
            d.arc([x + 0.30 * s, yy - 0.06 * s, x + 0.62 * s, yy + 0.06 * s], 0, 160,
                  fill=col, width=lw2)
            d.arc([x + 0.62 * s, yy - 0.06 * s, x + s, yy + 0.06 * s], 0, 160,
                  fill=col, width=lw2)

    elif kind == "virus":                     # enveloped virus with spikes
        r_out = 0.28 * s
        d.ellipse([cx - r_out, cy - r_out, cx + r_out, cy + r_out], outline=col, width=lw)
        for i in range(8):
            a = i * 45 * 3.14159265 / 180.0
            ca, sa = __import__("math").cos(a), __import__("math").sin(a)
            d.line([cx + ca * r_out, cy + sa * r_out,
                    cx + ca * 0.46 * s, cy + sa * 0.46 * s], fill=col, width=lw2)
            d.ellipse([cx + ca * 0.46 * s - 0.05 * s, cy + sa * 0.46 * s - 0.05 * s,
                       cx + ca * 0.46 * s + 0.05 * s, cy + sa * 0.46 * s + 0.05 * s], fill=col)

    elif kind == "drone":                     # quadcopter over a reticle
        d.line([x + 0.14 * s, y + 0.24 * s, x + 0.86 * s, y + 0.24 * s], fill=col, width=lw)
        for px in (0.14, 0.86):
            d.ellipse([x + px * s - 0.15 * s, y + 0.05 * s,
                       x + px * s + 0.15 * s, y + 0.22 * s], outline=col, width=lw2)
            d.line([x + px * s, y + 0.24 * s, x + px * s, y + 0.30 * s], fill=col, width=lw2)
        d.rectangle([cx - 0.07 * s, y + 0.20 * s, cx + 0.07 * s, y + 0.34 * s], fill=col)
        r = 0.19 * s
        for a0, a1 in ((25, 155), (205, 335)):
            d.arc([cx - r, y + 0.72 * s - r, cx + r, y + 0.72 * s + r], a0, a1, fill=RED, width=lw)
        d.line([cx - 0.07 * s, y + 0.72 * s, cx + 0.07 * s, y + 0.72 * s], fill=RED, width=lw2)
        d.line([cx, y + 0.65 * s, cx, y + 0.79 * s], fill=RED, width=lw2)

    elif kind == "train":                     # rail car on a track
        d.rounded_rectangle([x + 0.08 * s, y + 0.12 * s, x + 0.92 * s, y + 0.62 * s],
                            radius=max(2, round(0.10 * s)), fill=col)
        d.rectangle([x + 0.18 * s, y + 0.22 * s, x + 0.82 * s, y + 0.38 * s], fill=PAPER)
        d.rectangle([x + 0.18 * s, y + 0.45 * s, x + 0.44 * s, y + 0.55 * s], fill=PAPER)
        d.rectangle([x + 0.50 * s, y + 0.45 * s, x + 0.82 * s, y + 0.55 * s], fill=PAPER)
        d.line([x + 0.14 * s, y + 0.80 * s, x + 0.86 * s, y + 0.80 * s], fill=col, width=lw)
        for k in range(4):
            tx = x + 0.22 * s + k * 0.15 * s
            d.line([tx, y + 0.64 * s, tx, y + 0.76 * s], fill=col, width=lw2)

    elif kind == "exam":                      # answer sheet, big red tick beside it
        d.rounded_rectangle([x + 0.02 * s, y + 0.06 * s, x + 0.50 * s, y + 0.94 * s],
                            radius=2, outline=col, width=lw)
        for k in range(4):
            yy = y + 0.20 * s + k * 0.16 * s
            d.rectangle([x + 0.08 * s, yy - 0.03 * s, x + 0.14 * s, yy + 0.03 * s],
                        outline=col, width=lw2)
            d.line([x + 0.19 * s, yy, x + 0.43 * s, yy], fill=col, width=lw2)
        d.line([x + 0.57 * s, y + 0.60 * s, x + 0.70 * s, y + 0.90 * s], fill=RED, width=lw)
        d.line([x + 0.70 * s, y + 0.90 * s, x + 0.97 * s, y + 0.20 * s], fill=RED, width=lw)

    elif kind == "skyline":                   # buildings behind a barrier line
        d.line([x, y + 0.86 * s, x + s, y + 0.86 * s], fill=RED, width=lw)
        for bx, bw, bh in ((0.00, 0.24, 0.34), (0.28, 0.20, 0.52), (0.52, 0.18, 0.24),
                           (0.74, 0.26, 0.44)):
            left = x + bx * s + 1
            right = x + (bx + bw) * s - 1
            top = y + (0.84 - bh) * s
            d.rectangle([left, top, right, y + 0.84 * s], fill=col)
            for k in range(3):
                wy = top + (0.07 + k * 0.12) * s
                if wy + 0.05 * s < y + 0.82 * s:
                    d.rectangle([left + 0.05 * s, wy, left + 0.095 * s, wy + 0.05 * s],
                                fill=PAPER)
                    d.rectangle([right - 0.095 * s, wy, right - 0.05 * s, wy + 0.05 * s],
                                fill=PAPER)

    elif kind == "reticle":                   # crosshair
        d.ellipse([x + 0.02 * s, y + 0.02 * s, x + 0.98 * s, y + 0.98 * s],
                  outline=col, width=lw2)
        d.ellipse([cx - 0.20 * s, cy - 0.20 * s, cx + 0.20 * s, cy + 0.20 * s],
                  outline=col, width=lw)
        d.rectangle([cx - 0.05 * s, cy - 0.05 * s, cx + 0.05 * s, cy + 0.05 * s], fill=RED)
        for a, b in (((cx, y), (cx, cy - 0.22 * s)), ((cx, cy + 0.22 * s), (cx, y + s)),
                     ((x, cy), (cx - 0.22 * s, cy)), ((cx + 0.22 * s, cy), (x + s, cy))):
            d.line([a[0], a[1], b[0], b[1]], fill=col, width=lw)

    elif kind == "portico":                   # parliament: pediment, columns, steps
        d.polygon([(cx, y + 0.02 * s), (x + 0.94 * s, y + 0.28 * s),
                   (x + 0.06 * s, y + 0.28 * s)], fill=col)
        d.rectangle([x + 0.06 * s, y + 0.32 * s, x + 0.94 * s, y + 0.38 * s], fill=col)
        for k in range(4):
            bx = x + 0.14 * s + k * 0.20 * s
            d.rectangle([bx, y + 0.40 * s, bx + 0.10 * s, y + 0.80 * s], fill=col)
        d.rectangle([x + 0.04 * s, y + 0.84 * s, x + 0.96 * s, y + 0.94 * s], fill=col)

    elif kind == "flag":                      # waving flag on a pole
        d.line([x + 0.20 * s, y + 0.04 * s, x + 0.20 * s, y + s], fill=col, width=lw)
        d.polygon([(x + 0.24 * s, y + 0.08 * s), (x + 0.62 * s, y + 0.16 * s),
                   (x + 0.96 * s, y + 0.06 * s), (x + 0.96 * s, y + 0.40 * s),
                   (x + 0.62 * s, y + 0.50 * s), (x + 0.24 * s, y + 0.42 * s)], fill=col)
        for k in range(2):
            xx = x + (0.34 + 0.18 * k) * s
            d.line([xx, y + (0.15 + 0.03 * k) * s, xx, y + (0.34 + 0.02 * k) * s],
                   fill=PAPER, width=lw2)
        d.line([x + 0.04 * s, y + s - 1, x + 0.52 * s, y + s - 1], fill=col, width=lw)

    elif kind == "factory":                   # plant, chimney and smoke plume
        d.rectangle([x + 0.02 * s, y + 0.56 * s, x + 0.74 * s, y + 0.94 * s], fill=col)
        d.polygon([(x + 0.02 * s, y + 0.56 * s), (x + 0.26 * s, y + 0.38 * s),
                   (x + 0.26 * s, y + 0.56 * s), (x + 0.50 * s, y + 0.38 * s),
                   (x + 0.50 * s, y + 0.56 * s)], fill=col)
        d.rectangle([x + 0.78 * s, y + 0.42 * s, x + 0.90 * s, y + 0.94 * s], fill=col)
        d.rectangle([x + 0.74 * s, y + 0.38 * s, x + 0.94 * s, y + 0.43 * s], fill=col)
        for k in range(3):
            d.rectangle([x + (0.10 + 0.20 * k) * s, y + 0.66 * s,
                         x + (0.20 + 0.20 * k) * s, y + 0.76 * s], fill=PAPER)
        for ox, oy, r in ((0.84, 0.30, 0.05), (0.94, 0.20, 0.04), (0.80, 0.18, 0.035)):
            sx, sy = x + ox * s, y + oy * s
            d.ellipse([sx - r * s, sy - r * s, sx + r * s, sy + r * s],
                      fill=RED if oy == 0.30 else MUTED)

    elif kind == "scan":                      # screen with a cross
        d.rounded_rectangle([x + 0.03 * s, y + 0.08 * s, x + 0.97 * s, y + 0.92 * s],
                            radius=2, outline=col, width=lw)
        d.arc([x + 0.24 * s, y + 0.26 * s, x + 0.76 * s, y + 0.78 * s], 0, 360,
              fill=col, width=lw2)
        d.line([cx, y + 0.34 * s, cx, y + 0.70 * s], fill=RED, width=lw)
        d.line([cx - 0.16 * s, cy, cx + 0.16 * s, cy], fill=RED, width=lw)

    elif kind == "ball":                      # football
        d.ellipse([x + 1.5, y + 1.5, x + s - 1.5, y + s - 1.5], outline=col, width=lw)
        tri = [(cx, cy - 0.26 * s), (cx + 0.25 * s, cy - 0.06 * s),
               (cx + 0.15 * s, cy + 0.24 * s), (cx - 0.15 * s, cy + 0.24 * s),
               (cx - 0.25 * s, cy - 0.06 * s)]
        d.polygon(tri, fill=col)
        for px, py in tri:
            vx, vy = px - cx, py - cy
            n = (vx * vx + vy * vy) ** 0.5
            d.line([px, py, cx + vx / n * 0.55 * s, cy + vy / n * 0.55 * s], fill=col, width=lw2)


# ---------------------------------------------------------------- content
LEADS = [
    ("MIDDLE EAST", "WAR", "radar", "TEHRAN",
     "IRAN STRIKES US BASES IN BAHRAIN AS HORMUZ TANKERS BURN",
     "IRGC missiles and drones hit Al-Riffa and Awali, destroying Patriot radars. "
     "Trump says he is \u201cinclined\u201d to strike again if no deal by the New Year."),
    ("CLIMATE", "SUMMIT", "globe", "ANTALYA",
     "COP31 COLLAPSES WITH NO DEAL AS FOSSIL FUELS SPLIT THE SUMMIT",
     "Antalya talks end 44 hours into overtime, the longest UN climate summit, "
     "after the EU rejected a text that never named coal, oil or gas."),
    ("MARKETS", "BUSINESS", "chart", "SEOUL \u00b7 NEW YORK",
     "AI SELL-OFF: ASIA SLIDES, KOSPI -3.7%, WALL ST IN CORRECTION",
     "Nasdaq\u2019s worst week since 2020 spills into Monday. Seoul, Taipei and Hong Kong "
     "fall; Asian governments step up stock rescue efforts."),
]

GRID = [
    ("EUROPE", "WAR", "ship", "BENGHAZI",
     "SEA DRONES HIT A RUSSIAN WARSHIP AT LIBYA\u2019S BENGHAZI PORT",
     "Corvette Merkury burns; the war reaches the Mediterranean."),
    ("AFRICA", "CONFLICT", "virus", "ITURI, DR CONGO",
     "WHO PLEADS FOR PEACE AS FIGHTING HALTS THE EBOLA RESPONSE",
     "Staff sheltered 24 hours in a maternity ward in Ituri, DR Congo."),
    ("ASIA", "DIPLOMACY", "train", "DELHI",
     "NEPAL\u2019S PM IN DELHI FOR A $1.5BN PACKAGE AND A NEW TRAIN",
     "Modi and Balendra Shah flag off the Ayodhya\u2013Janakpur Express."),
    ("ASIA", "POLITICS", "exam", "SEOUL",
     "SOUTH KOREA\u2019S MINISTER QUITS OVER AI EXAM CHEATING",
     "Choi Kyo-jin resigns after CSAT anti-cheat chaos; Lee accepts."),
    ("MIDDLE EAST", "WAR", "skyline", "MAGHAZI",
     "GAZA: STRIKES KILL THREE AS ISRAEL PUSHES THE YELLOW LINE",
     "Maghazi camp 45% held or destroyed; the Board of Peace may quit."),
    ("AFRICA", "CONFLICT", "drone", "KHARTOUM",
     "DRONES HIT KHARTOUM: FOUR DEAD AND A UN BUILDING DAMAGED",
     "The RSF is blamed for strikes on the airport and government blocks."),
    ("HEALTH", "HEALTH", "scan", "UK",
     "WORLD\u2019S LARGEST AI BREAST-CANCER TRIAL OPENS IN THE UK",
     "700,000 women invited as the NHS tests AI reading of mammograms."),
    ("EUROPE", "WAR", "reticle", "WARSAW",
     "POLAND: RUSSIA TWICE TRIED TO KILL A UKRAINIAN RAPPER",
     "Warsaw names a sabotage campaign it says was run from abroad."),
    ("MIDDLE EAST", "POLITICS", "portico", "JERUSALEM",
     "LIKUD AND EISENKOT END COALITION TALKS WITH NO DEAL",
     "Israel\u2019s two blocs split on portfolios, leaving the mandate open."),
    ("AMERICAS", "POLITICS", "flag", "WASHINGTON",
     "TRUMP BLAMES THE MIDTERM LOSSES FOR THE MARKET WIPE-OUT",
     "Says Democratic wins triggered the slide; warns Schumer will be \u201cvery hard\u201d."),
    ("ASIA", "INDUSTRY", "factory", "JAVA",
     "INDONESIA FACTORY FIRE: 24 BODY BAGS CARRIED FROM THE RUINS",
     "Police recover the dead in Java as the search for the missing resumes."),
    ("SPORT", "SPORT", "ball", "ANFIELD",
     "LIVERPOOL 4-0 MANCHESTER UNITED: POCHETTINO\u2019S ROUT",
     "Ten-man United humbled in the Argentine\u2019s first match in charge."),
]

LEFT, RIGHT = 36, W - 36

# ---------------------------------------------------------------- masthead
d.rectangle([0, 0, W - 1, 7], fill=INK)
line(36, 20, "ONE DAY OF WORLD NEWS, ONE PICTURE", B12, MUTED)
line(RIGHT - tw("MONDAY", B12), 20, "MONDAY", B12, RED)
d.rectangle([36, 40, RIGHT, 42], fill=INK)
line(34, 46, "23 NOVEMBER 2026", SERIF, INK)
d.rectangle([36, 126, RIGHT, 128], fill=INK)
line(36, 134, "FIFTEEN STORIES REPORTED ON THE DAY, FROM EVERY REGION OF THE WORLD",
     B16, INK)
lead_in = ("15 stories   \u00b7   9 beats   \u00b7   Africa, the Americas, Asia, Europe "
           "and the Middle East   ")
lx = line(36, 158, lead_in, R13, MUTED)
d.ellipse([lx, 163.5, lx + 6, 169.5], fill=INK)
lx = line(lx + 11, 158, "several agencies", R13, MUTED) + 12
d.ellipse([lx, 163.5, lx + 6, 169.5], outline=INK, width=1)
line(lx + 11, 158, "one report", R13, MUTED)
d.rectangle([36, 178, RIGHT, 178], fill=RULE)

# ---------------------------------------------------------------- leads
GUT = 22
LEAD_COL = (RIGHT - LEFT - 2 * GUT) / 3.0
LEAD_TOP = 192
LEAD_H = 258
HEADS = (B21, B21, B21)          # measured: 24px breaks lead 1 badly
LHS = (25, 25, 25)
for i, (region, beat, kind, place, head, body) in enumerate(LEADS):
    x = LEFT + i * (LEAD_COL + GUT)
    if i:
        d.rectangle([x - GUT / 2.0 - 0.5, LEAD_TOP, x - GUT / 2.0 - 0.5,
                     LEAD_TOP + LEAD_H - 26], fill=RULE)
    # header row: chip, beat, picture; the headline then uses the full column
    end = chip(x, LEAD_TOP + 2, region, RED)
    line(end + 13, LEAD_TOP + 4, beat, B10, MUTED)
    glyph(kind, x + LEAD_COL - 42, LEAD_TOP - 2, 42)
    yy = block(x, LEAD_TOP + 46, LEAD_COL, head, HEADS[i], LHS[i])
    block(x, yy + 9, LEAD_COL, body, R13, 18, MUTED)
    line(x, LEAD_TOP + LEAD_H - 17, place, B10, MUTED)

d.rectangle([LEFT, LEAD_TOP + LEAD_H, RIGHT, LEAD_TOP + LEAD_H + 1], fill=INK)

# ---------------------------------------------------------------- grid
gy = LEAD_TOP + LEAD_H + 3
GGUT = 16
GCOL = (RIGHT - LEFT - 2 * GGUT) / 3.0
GHEAD = GCOL - 38                # headline column, clear of the 30px picture
rows = [GRID[r * 3:r * 3 + 3] for r in range(4)]


def cell_height(item):
    head, detail = item[4], item[5]
    return 27 + len(wrap(head, B15, GHEAD)) * 18 + 3 + len(wrap(detail, R11, GCOL)) * 14


heights = [max(cell_height(c) for c in row) for row in rows]
band = (H - 40 - gy) - (3 * 9)
extra = (band - sum(heights)) / 4.0
assert extra >= 0, ("grid overflows the footer by", -extra)
y = gy
for r, row in enumerate(rows):
    if r:
        d.rectangle([LEFT, y, RIGHT, y], fill=RULE)
        y += 1
    for c, item in enumerate(row):
        region, beat, kind, place, head, detail = item
        x = LEFT + c * (GCOL + GGUT)
        end = chip(x, y + 7, region, INK)
        line(end + 13, y + 9, place, B10, MUTED)
        glyph(kind, x + GCOL - 30, y + 3, 30)
        yt = block(x, y + 28, GHEAD, head, B15, 18)
        block(x, yt + 3, GCOL, detail, R11, 14, MUTED)
    y += heights[r] + 9 + extra

# ---------------------------------------------------------------- footer
d.rectangle([0, H - 40, W - 1, H - 1], fill=INK)
d.text((36, H - 29), "MONDAY 23 NOVEMBER 2026  \u00b7  THE WORLD IN ONE DAY",
       font=B12, fill=PAPER)
regs = "MIDDLE EAST \u00b7 EUROPE \u00b7 AFRICA \u00b7 ASIA \u00b7 AMERICAS"
d.text((RIGHT - tw(regs, B10), H - 27), regs, font=B10, fill=RULE)

here = os.path.dirname(os.path.abspath(__file__))
# ---------------------------------------------------------------- check
def overlap(a, b, pad=1):
    return (a[0] < b[2] - pad and b[0] < a[2] - pad and
            a[1] < b[3] - pad and b[1] < a[3] - pad)


for box in LAYOUT:
    assert box[0] >= LEFT - 8 and box[2] <= RIGHT + 1, ("text off the page", box)
    assert box[1] > 8 and box[3] < H - 40, ("text off the band", box)
for i, a in enumerate(LAYOUT):
    for b in LAYOUT[i + 1:]:
        assert not overlap(a, b, pad=2), ("text over text", a, b)
    for g in GLYPH_BOXES:
        assert not overlap(a, g[1:]), ("text over a pictogram", a, g)
for g in GLYPH_BOXES:
    assert g[1] >= LEFT and g[3] <= RIGHT, ("pictogram off the page", g)

img.save(os.path.join(here, "entry.png"), format="PNG", optimize=True)
print("wrote", os.path.join(here, "entry.png"), img.size,
      "%d text lines, %d pictograms, checks passed" % (len(LAYOUT), len(GLYPH_BOXES)))

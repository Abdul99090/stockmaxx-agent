#!/usr/bin/env python3
"""Render the StockMaxx Agent demo video (silent mp4) from the recorded
terminal transcript: title card -> scrolling terminal demo -> closing card.
Frames are drawn with PIL and encoded with ffmpeg."""
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAMES = os.path.join(ROOT, "video", "frames")
OUT = os.path.join(ROOT, "video", "demo.mp4")
W, H, FPS = 1280, 720, 2

BG = (13, 17, 23)
PANEL = (22, 27, 34)
FG = (230, 237, 243)
DIM = (139, 148, 158)
ACCENT = (0, 82, 255)      # Base blue
GREEN = (63, 185, 80)
YELLOW = (210, 153, 34)


def font(size, mono=True):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf" if mono else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


F_TITLE = font(64, mono=False)
F_SUB = font(30, mono=False)
F_TERM = font(21)
F_CARD = font(34, mono=False)
F_CARD_SM = font(26, mono=False)


def base_frame():
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)


def title_card():
    img, d = base_frame()
    d.rectangle([0, 0, W, 10], fill=ACCENT)
    d.text((80, 200), "StockMaxx Agent", font=F_TITLE, fill=FG)
    d.text((80, 300), "Agentic Stock Finance on Base", font=F_SUB, fill=ACCENT)
    d.text((80, 380), "Built for the Base Stocks Maxxing Builder Quest", font=F_SUB, fill=DIM)
    d.text((80, 470), "Live demo on Base Sepolia (testnet) - paper portfolio - no real funds", font=F_CARD_SM, fill=GREEN)
    d.text((80, 620), "An AI agent that scans tokenized stocks, scores signals,\nand trades only inside hard risk caps.", font=F_CARD_SM, fill=DIM)
    return img


def closing_card():
    img, d = base_frame()
    d.rectangle([0, 0, W, 10], fill=ACCENT)
    d.text((80, 90), "How it works", font=F_CARD, fill=FG)
    lines = [
        ("1. READ", "Tokenized Stocks API on Base: contracts, multiplier, NAV"),
        ("2. SCORE", "Momentum + consistency radar, with a NAV-staleness guard"),
        ("3. GUARD", "20% position cap - 60% exposure cap - stop-loss / take-profit"),
        ("4. EXECUTE", "Paper intents anchored to live Base Sepolia blocks"),
        ("5. REPORT", "Share-equivalent positions (balanceOfUI style) + ledger"),
    ]
    y = 170
    for head, body in lines:
        d.text((80, y), head, font=F_TERM, fill=ACCENT)
        d.text((300, y), body, font=F_TERM, fill=FG)
        y += 56
    d.text((80, 520), "Mainnet execution stays OFF until a human turns it on.", font=F_CARD_SM, fill=YELLOW)
    d.text((80, 580), "Repo: github.com/Abdul99090/stockmaxx-agent", font=F_CARD_SM, fill=DIM)
    d.text((80, 630), "@buildonbase  #StocksMaxxing", font=F_CARD_SM, fill=DIM)
    return img


def terminal_frame(lines, upto):
    img, d = base_frame()
    d.rectangle([40, 30, W - 40, H - 30], fill=PANEL)
    d.rectangle([40, 30, W - 40, 74], fill=(33, 38, 45))
    for i, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([64 + i * 30, 44, 80 + i * 30, 60], fill=col)
    d.text((180, 42), "stockmaxx-agent - Base Sepolia demo", font=F_TERM, fill=DIM)
    visible = lines[:upto]
    max_lines = 26
    visible = visible[-max_lines:]
    y = 96
    for line in visible:
        color = FG
        if "BUY" in line or "EXIT" in line:
            color = GREEN
        elif "blocked" in line:
            color = YELLOW
        elif line.startswith("=") or "SUMMARY" in line:
            color = ACCENT
        d.text((64, y), line[:104], font=F_TERM, fill=color)
        y += 23
    return img


def load_transcript_lines():
    path = os.path.join(ROOT, "output", "demo_transcript.txt")
    with open(path) as fh:
        raw = [ln.rstrip("\n") for ln in fh]
    keep = []
    for ln in raw:
        if ln.strip() == "":
            continue
        keep.append(ln)
    # compress: header block + every tick header + action/signal lines + summary
    picked, in_summary = [], False
    for ln in keep:
        if "PORTFOLIO SUMMARY" in ln:
            in_summary = True
        if in_summary or ln.startswith("-- tick") or "BUY" in ln or "EXIT" in ln or \
           ln.startswith("StockMaxx") or "live block" in ln or "Paper portfolio" in ln or \
           "Universe source" in ln or ln.startswith("="):
            picked.append(ln)
    return picked


def main():
    os.makedirs(FRAMES, exist_ok=True)
    for old in os.listdir(FRAMES):
        os.remove(os.path.join(FRAMES, old))
    frames = []
    title_secs, close_secs = 5, 8
    frames += [title_card()] * (title_secs * FPS)
    lines = load_transcript_lines()
    # reveal ~1 line per frame
    term_frames = []
    for upto in range(1, len(lines) + 1):
        term_frames.append(terminal_frame(lines, upto))
    # hold the final screen a bit
    term_frames += [term_frames[-1]] * (4 * FPS)
    frames += term_frames
    frames += [closing_card()] * (close_secs * FPS)
    for i, img in enumerate(frames):
        img.save(os.path.join(FRAMES, f"f{i:04d}.png"))
    dur = len(frames) / FPS
    print(f"{len(frames)} frames, ~{dur:.0f}s at {FPS} fps")
    subprocess.run(["ffmpeg", "-y", "-framerate", str(FPS), "-i", os.path.join(FRAMES, "f%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT],
                   check=True, capture_output=True)
    print("wrote", OUT)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""amdrome v1 sprite pack: 32x32 factory sprites, 16-color industrial palette.
Deterministic PIL drawing — regenerable, diffable, no external deps.
Output: assets/sprites/*.png + sheet.png (preview grid) + manifest.json"""
import json, os
from PIL import Image, ImageDraw

OUT = "/mnt/d/ops/amdrome/assets/sprites"
os.makedirs(OUT, exist_ok=True)
S = 32
PAL = {  # industrial 16
    "ink": "#1a1c2c", "steel_d": "#5d275d", "steel": "#b13e53", "steel_l": "#ef7d57",
    "metal_d": "#38b764", "metal": "#a7f070", "warn_y": "#ffcd75", "warn_o": "#f7a41d",
    "alert_r": "#e83b3b", "cool_b": "#41a6f6", "deep_b": "#3b5dc9", "hud": "#73eff7",
    "skin": "#f4d29c", "grey": "#94b0c2", "dark": "#333c57", "light": "#f4f4f4",
}
def px(d, x, y, c): d.point((x, y), fill=PAL[c])
def rect(d, x0, y0, x1, y1, c, fill=True):
    d.rectangle([x0, y0, x1, y1], fill=PAL[c] if fill else None, outline=PAL[c] if not fill else None)

def canvas():
    img = Image.new("RGB", (S, S), PAL["ink"])
    return img, ImageDraw.Draw(img)

def sprite_cnc():  # CNC mill: body + spindle + control panel
    img, d = canvas()
    rect(d, 4, 10, 27, 28, "grey"); rect(d, 4, 10, 27, 13, "dark")
    rect(d, 8, 14, 23, 20, "dark"); rect(d, 14, 8, 17, 14, "steel")   # spindle housing
    rect(d, 15, 14, 16, 18, "steel_l")                                # tool
    rect(d, 5, 22, 12, 27, "metal_d")                                 # workpiece bay
    rect(d, 22, 22, 26, 26, "deep_b")                                 # control panel
    px(d, 23, 23, "hud"); px(d, 25, 23, "alert_r")
    return img

def sprite_arm():  # assembly robot arm on base
    img, d = canvas()
    rect(d, 6, 24, 25, 28, "dark"); rect(d, 10, 22, 21, 24, "grey")
    d.line([15, 22, 22, 10], fill=PAL["steel"], width=4)              # upper arm
    d.line([22, 10, 10, 6], fill=PAL["steel_l"], width=3)             # forearm
    px(d, 15, 21, "warn_y")
    rect(d, 8, 4, 12, 8, "steel")                                     # gripper head
    px(d, 9, 9, "hud"); px(d, 23, 9, "hud")
    return img

def sprite_conveyor():  # conveyor segment with rollers + moving crate
    img, d = canvas()
    rect(d, 2, 18, 29, 24, "dark")
    for x in range(4, 29, 6): d.ellipse([x, 19, x+4, 23], fill=PAL["grey"], outline=PAL["ink"])
    rect(d, 10, 10, 21, 17, "warn_y"); rect(d, 10, 10, 21, 12, "warn_o")  # crate
    rect(d, 2, 25, 29, 27, "metal_d")
    return img

def sprite_qa():  # QA scanner gantry
    img, d = canvas()
    rect(d, 4, 4, 7, 28, "grey"); rect(d, 24, 4, 27, 28, "grey")
    rect(d, 4, 4, 27, 8, "dark")
    rect(d, 12, 10, 19, 16, "deep_b"); rect(d, 13, 11, 18, 13, "hud")  # scanner head
    d.line([15, 16, 15, 26], fill=PAL["alert_r"], width=1)
    d.line([13, 20, 18, 20], fill=PAL["metal_d"], width=1)
    return img

def sprite_worker():  # operator with hard hat
    img, d = canvas()
    rect(d, 13, 3, 18, 6, "warn_y")                                   # hard hat
    rect(d, 13, 7, 18, 12, "skin")                                    # face
    rect(d, 11, 13, 20, 22, "deep_b")                                 # torso (overalls)
    rect(d, 12, 23, 15, 29, "dark"); rect(d, 16, 23, 19, 29, "dark")  # legs
    rect(d, 8, 14, 11, 20, "skin"); rect(d, 20, 14, 23, 20, "skin")   # arms
    px(d, 14, 9, "ink"); px(d, 17, 9, "ink")
    return img

def sprite_agv():  # autonomous flat cart
    img, d = canvas()
    rect(d, 5, 16, 26, 24, "steel"); rect(d, 5, 16, 26, 18, "steel_l")
    rect(d, 9, 11, 22, 16, "warn_y")                                  # load
    d.ellipse([8, 24, 14, 29], fill=PAL["ink"], outline=PAL["grey"])
    d.ellipse([17, 24, 23, 29], fill=PAL["ink"], outline=PAL["grey"])
    px(d, 25, 15, "hud")
    return img

def sprite_andon():  # andon signal tower
    img, d = canvas()
    rect(d, 14, 6, 17, 28, "grey")
    rect(d, 12, 4, 19, 9, "alert_r"); rect(d, 12, 10, 19, 15, "warn_y"); rect(d, 12, 16, 19, 21, "metal_d")
    px(d, 14, 6, "light"); px(d, 14, 12, "light"); px(d, 14, 18, "light")
    rect(d, 10, 28, 21, 30, "dark")
    return img

def sprite_alert():  # UI: alert triangle
    img, d = canvas()
    d.polygon([(16, 4), (29, 27), (3, 27)], fill=PAL["warn_y"], outline=PAL["ink"])
    rect(d, 15, 12, 17, 20, "ink"); px(d, 15, 23, "ink"); px(d, 16, 23, "ink"); px(d, 17, 23, "ink")
    return img

def sprite_gauge():  # UI: health gauge
    img, d = canvas()
    d.ellipse([3, 6, 29, 27], fill=PAL["dark"], outline=PAL["grey"])
    d.line([16, 17, 25, 10], fill=PAL["alert_r"], width=2)
    px(d, 16, 17, "light")
    return img

SPRITES = {
    "station_cnc": sprite_cnc, "station_arm": sprite_arm, "conveyor": sprite_conveyor,
    "station_qa": sprite_qa, "worker": sprite_worker, "agv": sprite_agv,
    "andon": sprite_andon, "ui_alert": sprite_alert, "ui_gauge": sprite_gauge,
}
manifest = {}
for name, fn in SPRITES.items():
    img = fn()
    img.save(f"{OUT}/{name}.png")
    manifest[name] = {"file": f"{name}.png", "size": "32x32", "palette": "industrial16"}
# preview sheet 3x3
sheet = Image.new("RGB", (S*3 + 16, S*3 + 16), PAL["dark"])
for i, name in enumerate(SPRITES):
    img = Image.open(f"{OUT}/{name}.png")
    sheet.paste(img, (8 + (i % 3) * (S + 4), 8 + (i // 3) * (S + 4)))
sheet.save(f"{OUT}/sheet.png")
json.dump({"palette": PAL, "sprites": manifest}, open(f"{OUT}/manifest.json", "w"), indent=1)
print("wrote", len(SPRITES), "sprites + sheet.png to", OUT)

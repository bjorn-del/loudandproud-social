#!/usr/bin/env python3
"""Render a 9:16 product slideshow video (YouTube Shorts / TikTok / Reels).

usage: make_video.py OUT.mp4 "TITLE" "PRICE" "URL" img1 img2 ...
"""
import subprocess, sys, os, tempfile

W, H, FPS = 1080, 1920, 30
SLIDE, FADE, END = 3.0, 0.5, 3.0
FONT_B = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
FONT_M = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"
ACCENT = "0xE8452C"


def esc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")


def run(args):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], check=True)


def slide(img, out, dur, zoom_in):
    n = int(dur * FPS)
    z = f"1+0.08*on/{n}" if zoom_in else f"1.08-0.08*on/{n}"
    from PIL import Image
    iw, ih = Image.open(img).size
    fg_h = min(1100, int(W * ih / iw)) // 2 * 2
    fc = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
        f"boxblur=30:2,eq=brightness=-0.25[bg];"
        f"[0:v]scale={W*2}:{fg_h*2}:force_original_aspect_ratio=decrease,"
        f"pad={W*2}:{fg_h*2}:(ow-iw)/2:(oh-ih)/2:color=black@0,"
        f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{fg_h}:fps={FPS}[fg];"
        f"[bg]loop=loop={n}:size=1,setpts=N/{FPS}/TB[bgl];"
        f"[bgl][fg]overlay=0:(H-h)/2-80:shortest=1,format=yuv420p[v]"
    )
    run(["-i", img, "-filter_complex", fc, "-map", "[v]", "-t", str(dur),
         "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", out])


def end_card(img, out, dur, title, price, url):
    fc = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
        f"boxblur=40:2,eq=brightness=-0.45,loop=loop={int(dur*FPS)}:size=1,setpts=N/{FPS}/TB,"
        f"drawtext=fontfile={FONT_B}:text='{esc(title)}':fontsize=78:fontcolor=white:"
        f"x=(w-tw)/2:y=h*0.36,"
        f"drawtext=fontfile={FONT_B}:text='{esc(price)}':fontsize=120:fontcolor={ACCENT}:"
        f"x=(w-tw)/2:y=h*0.45,"
        f"drawtext=fontfile={FONT_M}:text='Worldwide shipping':fontsize=48:fontcolor=white@0.85:"
        f"x=(w-tw)/2:y=h*0.56,"
        f"drawtext=fontfile={FONT_B}:text='{esc(url)}':fontsize=52:fontcolor=white:"
        f"box=1:boxcolor={ACCENT}:boxborderw=28:x=(w-tw)/2:y=h*0.66,"
        f"fade=t=in:st=0:d=0.4,format=yuv420p[v]"
    )
    run(["-i", img, "-filter_complex", fc, "-map", "[v]", "-t", str(dur),
         "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", out])


def main():
    out, title, price, url, *imgs = sys.argv[1:]
    imgs = imgs[:5]
    tmp = tempfile.mkdtemp()
    clips = []
    for i, img in enumerate(imgs):
        c = os.path.join(tmp, f"s{i}.mp4")
        slide(img, c, SLIDE + FADE, i % 2 == 0)
        clips.append((c, SLIDE + FADE))
    c = os.path.join(tmp, "end.mp4")
    end_card(imgs[0], c, END, title, price, url)
    clips.append((c, END))

    # chain xfades
    inputs, fc, prev, offset = [], [], "0:v", 0.0
    for i, (c, d) in enumerate(clips):
        inputs += ["-i", c]
    for i in range(1, len(clips)):
        offset += clips[i - 1][1] - FADE
        lab = f"x{i}"
        fc.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={FADE}:offset={offset:.2f}[{lab}]")
        prev = lab
    total = offset + clips[-1][1]
    # persistent overlay: brand on top, title + price on bottom (hidden during end card)
    t_end = total - END
    fc.append(
        f"[{prev}]drawtext=fontfile={FONT_B}:text='LOUDANDPROUD':fontsize=40:fontcolor=white@0.9:"
        f"x=(w-tw)/2:y=140,"
        f"drawtext=fontfile={FONT_B}:text='{esc(title)}':fontsize=70:fontcolor=white:"
        f"x=(w-tw)/2:y=h-400:enable='lt(t,{t_end:.2f})',"
        f"drawtext=fontfile={FONT_B}:text='{esc(price)}':fontsize=84:fontcolor={ACCENT}:"
        f"x=(w-tw)/2:y=h-300:enable='lt(t,{t_end:.2f})',"
        f"format=yuv420p[v]"
    )
    run([*inputs, "-f", "lavfi", "-t", f"{total:.2f}", "-i", "anullsrc=r=44100:cl=stereo",
         "-filter_complex", ";".join(fc), "-map", "[v]", "-map", f"{len(clips)}:a",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "128k",
         "-movflags", "+faststart", "-shortest", out])
    print(f"{out}: {total:.1f}s")


if __name__ == "__main__":
    main()

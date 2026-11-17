"""Clip -> 9:16 (Blur-Hintergrund + zentriertes Original), Credit-Overlay, optional Untertitel."""
import pathlib, subprocess, shutil, tempfile

FONT = next((p for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                         "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                         "C:/Windows/Fonts/arialbd.ttf"] if pathlib.Path(p).exists()), None)


def download(url, dest):
    subprocess.run(["yt-dlp", "-q", "--no-warnings", "-f", "best", "-o", str(dest), url], check=True)


def _esc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")


def captions(video, srt):
    from faster_whisper import WhisperModel      # optional dependency
    segs, _ = WhisperModel("small", compute_type="int8").transcribe(str(video), vad_filter=True)
    ts = lambda x: f"{int(x//3600):02}:{int(x%3600//60):02}:{int(x%60):02},{int(x%1*1000):03}"
    with open(srt, "w", encoding="utf-8") as f:
        for i, s in enumerate(segs, 1):
            f.write(f"{i}\n{ts(s.start)} --> {ts(s.end)}\n{s.text.strip()}\n\n")
    return srt


def to_vertical(src, dst, credit, w=1080, h=1920, with_captions=False):
    fg_h = int(w * 9 / 16)
    vf = (f"[0:v]split[a][b];"
          f"[a]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur=30:6,eq=brightness=-0.1[bg];"
          f"[b]scale={w}:{fg_h}[fg];[bg][fg]overlay=0:(H-h)/2[v]")
    last = "v"
    if FONT and credit:
        vf += (f";[{last}]drawtext=fontfile={FONT}:text='{_esc(credit)}':fontcolor=white:fontsize=44:"
               f"borderw=3:bordercolor=black:x=(w-text_w)/2:y=(h+{fg_h})/2+40[v2]")
        last = "v2"
    if with_captions:
        srt = pathlib.Path(tempfile.mkdtemp()) / "c.srt"
        captions(src, srt)
        style = "FontSize=16,Bold=1,Outline=3,Alignment=2,MarginV=380"
        vf += f";[{last}]subtitles={srt}:force_style='{style}'[v3]"
        last = "v3"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-filter_complex", vf,
                    "-map", f"[{last}]", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(dst)],
                   check=True)

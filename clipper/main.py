import argparse, asyncio, json, pathlib, time, yaml
from . import twitch, chat, render


def load(path):
    return yaml.safe_load(open(path, encoding="utf-8"))


class Pipeline:
    def __init__(self, cfg):
        self.cfg = cfg
        self.out = pathlib.Path(cfg["output_dir"]); self.out.mkdir(exist_ok=True)
        self.streams = {}
        self.clip_times = []
        self.monitor = chat.ChatMonitor(cfg["spike"], self.on_spike)

    async def refresh_loop(self):
        fixed = self.cfg.get("channels") or []
        gid = None if fixed else await asyncio.to_thread(twitch.game_id, self.cfg["game"])
        while True:
            if fixed:   # nur Kanäle aus Clipping-Programmen, sobald sie live sind
                top = await asyncio.to_thread(twitch.live_by_login, fixed)
            else:
                top = await asyncio.to_thread(twitch.top_streams, gid, self.cfg["top_n"], self.cfg["languages"])
            self.streams = {s["login"]: s for s in top}
            await self.monitor.set_channels(self.streams)
            print(f"[streams] beobachte: " + ", ".join(f"{s['name']}({s['viewers']})" for s in top))
            await asyncio.sleep(self.cfg["refresh_streams_every"])

    async def on_spike(self, login, ratio):
        now = time.time()
        self.clip_times = [t for t in self.clip_times if t > now - 3600]
        if len(self.clip_times) >= self.cfg["clip"]["max_clips_per_hour"]:
            return
        self.clip_times.append(now)
        s = self.streams[login]
        print(f"[spike] {s['name']}  x{ratio:.1f} -> erstelle Clip")
        try:
            await asyncio.to_thread(self.make_clip, s, ratio)
        except Exception as e:
            print(f"[fehler] {login}: {e}")

    def make_clip(self, s, ratio):
        cid = twitch.create_clip(s["user_id"], self.cfg["clip"]["duration"])
        meta = twitch.wait_clip(cid)
        if not meta:
            raise RuntimeError("Clip wurde nicht rechtzeitig verarbeitet")
        stamp = time.strftime("%Y%m%d-%H%M%S")
        base = self.out / f"{stamp}_{s['login']}"
        raw = base.with_suffix(".raw.mp4"); final = base.with_suffix(".mp4")
        render.download(meta["url"], raw)
        r = self.cfg["render"]
        render.to_vertical(raw, final, f"twitch.tv/{s['login']}", r["width"], r["height"], r["captions"])
        raw.unlink(missing_ok=True)
        tags = " ".join(r["hashtags"])
        base.with_suffix(".json").write_text(json.dumps({
            "streamer": s["name"], "clip_url": meta["url"], "viewers": s["viewers"],
            "spike_ratio": round(ratio, 1), "stream_title": s["title"],
            "caption": f"{s['name']} dreht durch 😳 (Clip: twitch.tv/{s['login']}) {tags}"},
            ensure_ascii=False, indent=2))
        print(f"[fertig] {final}")

    async def run(self):
        await asyncio.gather(self.refresh_loop(), self.monitor.run())


def main():
    ap = argparse.ArgumentParser(prog="clipper")
    ap.add_argument("cmd", choices=["auth", "run", "render"])
    ap.add_argument("-c", "--config", default="clipper/config.yaml")
    ap.add_argument("files", nargs="*", help="render: Eingabe.mp4 Ausgabe.mp4")
    a = ap.parse_args()
    cfg = load(a.config)
    if a.cmd == "auth":
        twitch.device_login()
    elif a.cmd == "render":
        r = cfg["render"]
        render.to_vertical(a.files[0], a.files[1], "twitch.tv/test", r["width"], r["height"], r["captions"])
    else:
        asyncio.run(Pipeline(cfg).run())

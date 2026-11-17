"""Anonymer Twitch-Chat-Listener + Spike-Erkennung (Chat-Rate gegen Baseline)."""
import asyncio, collections, time

HOST, PORT = "irc.chat.twitch.tv", 6667


class Channel:
    def __init__(self, cfg):
        self.cfg = cfg
        self.events = collections.deque()      # (timestamp, gewicht)
        self.last_clip = 0.0

    def add(self, text):
        w = 1.0
        words = {x.strip("!?.,").upper() for x in text.split()}
        if words & {h.upper() for h in self.cfg["hype_words"]}:
            w = 1.5
        now = time.time()
        self.events.append((now, w))
        cutoff = now - self.cfg["baseline_window"]
        while self.events and self.events[0][0] < cutoff:
            self.events.popleft()

    def score(self):
        """(aktuelle Rate, Baseline-Rate, Nachrichten im Fenster) – Rate in Gewicht/Sek."""
        now = time.time()
        win, base = self.cfg["window"], self.cfg["baseline_window"]
        recent = [(t, w) for t, w in self.events if t >= now - win]
        older = sum(w for t, w in self.events if t < now - win)
        recent_rate = sum(w for _, w in recent) / win
        base_span = max(base - win, 1)
        elapsed = now - self.events[0][0] if self.events else 0
        base_rate = older / max(min(base_span, elapsed - win), 30)  # min 30s, gegen Division-Spikes
        return recent_rate, base_rate, len(recent)

    def is_spike(self):
        c = self.cfg
        rate, base, n = self.score()
        if n < c["min_msgs_in_window"] or time.time() - self.last_clip < c["cooldown"]:
            return None
        if rate >= c["ratio"] * max(base, 0.2):
            return rate / max(base, 0.2)
        return None


class ChatMonitor:
    def __init__(self, cfg, on_spike):
        self.cfg, self.on_spike = cfg, on_spike
        self.channels: dict[str, Channel] = {}
        self.writer = None

    async def set_channels(self, logins):
        logins = set(logins)
        if self.writer:
            for l in logins - self.channels.keys():
                self.writer.write(f"JOIN #{l}\r\n".encode())
            for l in self.channels.keys() - logins:
                self.writer.write(f"PART #{l}\r\n".encode())
                del self.channels[l]
        for l in logins:
            self.channels.setdefault(l, Channel(self.cfg))

    async def run(self):
        asyncio.create_task(self._watch())
        while True:
            try:
                reader, self.writer = await asyncio.open_connection(HOST, PORT)
                self.writer.write(b"NICK justinfan48213\r\n")
                for l in self.channels:
                    self.writer.write(f"JOIN #{l}\r\n".encode())
                async for raw in reader:
                    self._line(raw.decode(errors="ignore").rstrip())
            except (OSError, asyncio.IncompleteReadError):
                pass
            print("[chat] Verbindung weg, reconnect in 5s")
            await asyncio.sleep(5)

    def _line(self, line):
        if line.startswith("PING"):
            self.writer.write(b"PONG :tmi.twitch.tv\r\n")
        elif " PRIVMSG #" in line:
            head, _, rest = line.partition(" PRIVMSG #")
            login, _, text = rest.partition(" :")
            ch = self.channels.get(login)
            if ch:
                ch.add(text)

    async def _watch(self):
        while True:
            await asyncio.sleep(1)
            for login, ch in list(self.channels.items()):
                ratio = ch.is_spike()
                if ratio:
                    ch.last_clip = time.time()
                    asyncio.create_task(self.on_spike(login, ratio))

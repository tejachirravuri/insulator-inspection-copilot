"""Capture README screenshots of the running app with headless Microsoft Edge (or Chrome).

    python scripts/capture_screenshots.py --url http://localhost:8000 \
        --question "Which inspections need a human review?" --out docs/images/agent_chat.png

Drives the browser over the Chrome DevTools Protocol: opens the page, asks the question
through the real UI (one real Claude call), waits for the answer, expands sources and the
agent trace, and saves a PNG. Nothing is mocked: the screenshot shows a real response.
"""

import argparse
import asyncio
import base64
import json
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import websockets

BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]
PORT = 9333
ANSWER_DONE = (
    "(() => { const b = [...document.querySelectorAll('#messages .msg.assistant .bubble')]"
    ".pop(); return b && !b.querySelector('.spinner'); })()"
)


class Page:
    def __init__(self, ws) -> None:
        self.ws, self.next_id = ws, 0

    async def call(self, method: str, **params):
        self.next_id += 1
        await self.ws.send(json.dumps({"id": self.next_id, "method": method, "params": params}))
        while True:
            message = json.loads(await self.ws.recv())
            if message.get("id") == self.next_id:
                return message.get("result", {})

    async def js(self, expression: str):
        result = await self.call(
            "Runtime.evaluate", expression=expression, awaitPromise=True, returnByValue=True
        )
        return result.get("result", {}).get("value")

    async def wait_for(self, expression: str, seconds: float) -> None:
        async with asyncio.timeout(seconds):
            # Polling is right here: the state lives in the remote browser, not in this process.
            while not await self.js(expression):  # noqa: ASYNC110
                await asyncio.sleep(1)


async def capture(
    ws_url: str, url: str, question: str | None, width: int, height: int, inspection: int | None
) -> tuple[bytes, bytes | None]:
    """Returns (viewport screenshot, extra screenshot or None).

    Extra: the full answer bubble when a question is asked, or the inspection viewer panel
    when --inspection is given.
    """
    async with websockets.connect(ws_url, max_size=50_000_000) as ws:
        page = Page(ws)
        await page.call(
            "Emulation.setDeviceMetricsOverride",
            width=width,
            height=height,
            deviceScaleFactor=1,
            mobile=False,
        )
        await page.call("Page.enable")
        await page.call("Page.navigate", url=url)
        await page.wait_for("document.querySelectorAll('.list-item').length > 0", 60)
        if inspection is not None:
            await page.js(f"show({int(inspection)})")
            await page.wait_for(
                "(() => { const i = document.querySelector('#viewer img');"
                " return i && i.complete && i.naturalWidth > 0; })()",
                60,
            )
        if question:
            await page.js(f"ask({json.dumps(question)})")
            await page.wait_for(ANSWER_DONE, 300)
            await page.js(
                "document.querySelectorAll('#messages details').forEach(d => d.open = true)"
            )
            await page.js("document.querySelector('#messages').scrollTop = 0")
        await asyncio.sleep(2)
        shot = await page.call("Page.captureScreenshot", format="png")
        answer = None
        if inspection is not None and not question:
            box = await page.js(
                "(() => { const r = document.querySelector('#viewer').getBoundingClientRect();"
                " return {x: r.x, y: r.y, width: r.width, height: r.height}; })()"
            )
            clip = await page.call("Page.captureScreenshot", format="png", clip={**box, "scale": 1})
            answer = base64.b64decode(clip["data"])
        if question:
            # The whole answer bubble (sources and trace included): let the layout grow to full
            # height so nothing is clipped by a scroll container, then measure and capture.
            await page.js(
                "document.querySelector('main').style.height = 'auto';"
                "document.querySelectorAll('section, #messages').forEach("
                "e => { e.style.overflow = 'visible'; e.style.maxHeight = 'none'; })"
            )
            await asyncio.sleep(1)
            box = await page.js(
                "(() => { const r = [...document.querySelectorAll("
                "'#messages .msg.assistant .bubble')].pop().getBoundingClientRect();"
                " return {x: r.x, y: r.y + window.scrollY, width: r.width, height: r.height}; })()"
            )
            clip = await page.call(
                "Page.captureScreenshot",
                format="png",
                captureBeyondViewport=True,
                clip={**box, "scale": 1},
            )
            answer = base64.b64decode(clip["data"])
        return base64.b64decode(shot["data"]), answer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--question")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--width", type=int, default=1500)
    parser.add_argument("--height", type=int, default=1000)
    parser.add_argument("--inspection", type=int, help="open this inspection (viewer screenshot)")
    args = parser.parse_args()

    browser = next(b for b in BROWSERS if Path(b).exists())
    # ignore_cleanup_errors: on Windows the browser may still hold profile files briefly.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        process = subprocess.Popen(
            [
                browser,
                "--headless=new",
                f"--remote-debugging-port={PORT}",
                f"--user-data-dir={profile}",
                "--hide-scrollbars",
                "about:blank",
            ]
        )
        try:
            for _ in range(30):
                try:
                    urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=1)
                    break
                except OSError:
                    time.sleep(0.5)
            targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list"))
            ws_url = next(t for t in targets if t["type"] == "page")["webSocketDebuggerUrl"]
            png, answer = asyncio.run(
                capture(ws_url, args.url, args.question, args.width, args.height, args.inspection)
            )
        finally:
            process.terminate()
            process.wait(timeout=30)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(png)
    print(f"saved {args.out} ({len(png) // 1024} KB)")
    if answer:
        suffix = "_answer.png" if args.question else "_viewer.png"
        answer_path = args.out.with_name(args.out.stem + suffix)
        answer_path.write_bytes(answer)
        print(f"saved {answer_path} ({len(answer) // 1024} KB)")


if __name__ == "__main__":
    main()

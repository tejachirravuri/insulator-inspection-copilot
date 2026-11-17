"""Load sample drone images into the local database by running detection on them.

    python scripts/seed_demo.py --folder "G:/path/to/images" --type glass --n 6

Images are copied to data/uploads/ (git-ignored). Only use images you are allowed to use;
do not publish dataset images without checking the dataset licence.
"""

import argparse
import asyncio
import random
from pathlib import Path

from inspection_copilot import services
from inspection_copilot.db import get_engine, get_sessionmaker


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", required=True)
    parser.add_argument("--type", default="glass", choices=["glass", "porcelain", "composite"])
    parser.add_argument("--mode", default="auto", choices=["auto", "fast", "accurate"])
    parser.add_argument("--n", type=int, default=6)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    files = sorted(
        p
        for p in Path(args.folder).rglob("*")  # noqa: ASYNC240 (CLI script, blocking is fine)
        if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    random.Random(args.seed).shuffle(files)
    async with get_sessionmaker()() as session:
        for path in files[: args.n]:
            image_id = await services.inspect_image(
                session,
                path.read_bytes(),
                path.name,
                args.type,
                args.mode,  # noqa: ASYNC240
            )
            detail = await services.image_detail(session, image_id)
            run = detail["run"]
            print(
                f"#{image_id} {path.name}: {len(detail['detections'])} insulators, "
                f"{run['model']} ({'escalated' if run['escalated'] else run['mode']}), "
                f"{run['inference_ms']:.0f} ms"
            )
    await get_engine().dispose()


if __name__ == "__main__":
    asyncio.run(main())

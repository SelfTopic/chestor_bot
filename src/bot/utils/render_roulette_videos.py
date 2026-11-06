import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from src.bot.services.roulette.positions import clips
from src.bot.services.roulette.spin_video import render_spin_video, spin_video_name
from src.bot.services.roulette.video_set import pack

# Рендер всего набора для релиза: запускается на GitHub, а не на сервере, поэтому на всех ядрах.
if __name__ == "__main__":
    archive = Path(sys.argv[1])
    with tempfile.TemporaryDirectory() as folder, ProcessPoolExecutor() as pool:
        paths = [Path(folder) / spin_video_name(clip) for clip in clips()]
        for done, path in enumerate(pool.map(render_spin_video, clips(), paths), 1):
            print(f"{done}/{len(paths)} {path.name}", flush=True)
        pack(Path(folder), archive)
    print(f"Набор роликов рулетки: {archive}")

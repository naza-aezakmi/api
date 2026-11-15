import asyncio
import json
import os
from pathlib import Path


class TerrainEngine:
    def __init__(self) -> None:
        self._process: asyncio.subprocess.Process | None = None
        self._lock = asyncio.Lock()

    async def search(self, planet: str, lat: float, lon: float, weights: dict[str, float]) -> dict:
        async with self._lock:
            if self._process is None or self._process.returncode is not None:
                self._process = await asyncio.create_subprocess_exec(
                    "node", str(Path(__file__).with_suffix(".cjs")),
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    env=os.environ.copy(),
                )
            process = self._process
            assert process.stdin is not None and process.stdout is not None
            try:
                process.stdin.write((json.dumps({
                    "planet": planet, "lat": lat, "lon": lon, "weights": weights,
                }) + "\n").encode())
                await process.stdin.drain()
                line = await asyncio.wait_for(process.stdout.readline(), timeout=60)
                if not line:
                    raise RuntimeError("Terrain engine exited")
                result = json.loads(line)
                if result.get("kind") != "results":
                    raise RuntimeError("Terrain engine could not read the index")
                return result
            except (OSError, RuntimeError, ValueError, asyncio.TimeoutError, asyncio.CancelledError):
                process.kill()
                await process.wait()
                self._process = None
                raise


engine = TerrainEngine()

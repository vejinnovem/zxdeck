"""Run tape decoding and ALSA writes outside the touchscreen process."""

from __future__ import annotations

from dataclasses import dataclass
import multiprocessing
from pathlib import Path
import queue
import subprocess
from typing import Literal

from zxdeck.audio.pcm import write_pcm
from zxdeck.tape.pulses import iter_tape_events


@dataclass(frozen=True, slots=True)
class PlaybackEvent:
    kind: Literal["started", "finished", "stopped", "error"]
    message: str = ""


class AudioPlayer:
    """Small controller for one disposable playback worker process."""

    def __init__(self, device: str = "default", sample_rate: int = 44_100) -> None:
        self.device = device
        self.sample_rate = sample_rate
        self._process = None
        self._cancel = None
        self._events = None

    @property
    def active(self) -> bool:
        return self._process is not None and self._process.is_alive()

    def play(self, path: str | Path) -> None:
        self.stop()
        context = multiprocessing.get_context("spawn")
        self._cancel = context.Event()
        self._events = context.Queue()
        self._process = context.Process(
            target=_play_worker,
            args=(
                str(Path(path)),
                self.device,
                self.sample_rate,
                self._cancel,
                self._events,
            ),
            name="zxdeck-audio",
            daemon=True,
        )
        self._process.start()

    def stop(self) -> None:
        process = self._process
        if process is None:
            self._close_ipc()
            return
        if process.is_alive() and self._cancel is not None:
            self._cancel.set()
            process.join(timeout=1.0)
        if process.is_alive():
            process.terminate()
            process.join(timeout=1.0)
        self._close_ipc()

    def poll(self) -> PlaybackEvent | None:
        if self._events is None:
            return None
        latest = None
        while True:
            try:
                latest = self._events.get_nowait()
            except queue.Empty:
                if (
                    latest is not None
                    and latest.kind in {"finished", "stopped", "error"}
                    and self._process is not None
                ):
                    self._process.join(timeout=0.2)
                    if not self._process.is_alive():
                        self._close_ipc()
                return latest

    def close(self) -> None:
        self.stop()

    def _close_ipc(self) -> None:
        events = self._events
        if events is not None:
            events.close()
            events.join_thread()
        self._process = None
        self._cancel = None
        self._events = None


def _play_worker(path, device, sample_rate, cancelled, events) -> None:
    command = (
        "aplay",
        "-q",
        "-D",
        device,
        "-t",
        "raw",
        "-f",
        "U8",
        "-c",
        "1",
        "-r",
        str(sample_rate),
    )
    player = None
    try:
        player = subprocess.Popen(command, stdin=subprocess.PIPE)
        if player.stdin is None:
            raise RuntimeError("cannot open ALSA input pipe")
        events.put(PlaybackEvent("started"))
        write_pcm(
            iter_tape_events(path),
            player.stdin,
            sample_rate=sample_rate,
            cancelled=cancelled.is_set,
        )
        player.stdin.close()
        return_code = player.wait()
        if cancelled.is_set():
            events.put(PlaybackEvent("stopped"))
        elif return_code:
            events.put(PlaybackEvent("error", f"ALSA EXIT {return_code}"))
        else:
            events.put(PlaybackEvent("finished"))
    except BrokenPipeError:
        events.put(PlaybackEvent("error", "AUDIO DEVICE UNAVAILABLE"))
    except Exception as exc:
        events.put(PlaybackEvent("error", str(exc)))
    finally:
        if player is not None and player.poll() is None:
            player.terminate()
            try:
                player.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                player.kill()

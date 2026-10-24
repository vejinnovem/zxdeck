"""Run tape decoding and ALSA writes outside the touchscreen process."""

from __future__ import annotations

from dataclasses import dataclass
import multiprocessing
from pathlib import Path
import queue
import subprocess
from typing import Literal

from zxdeck.audio.pcm import count_pcm_samples, write_pcm
from zxdeck.tape import TapeStop, selected_event_index
from zxdeck.tape.pulses import iter_tape_events


TapePhase = Literal["pilot", "data", "pause"]


@dataclass(frozen=True, slots=True)
class PlaybackEvent:
    kind: Literal["started", "progress", "finished", "stopped", "error"]
    message: str = ""
    position_seconds: float | None = None
    duration_seconds: float | None = None
    phase: TapePhase | None = None


class AudioPlayer:
    """Small controller for one disposable playback worker process."""

    def __init__(
        self,
        device: str = "default",
        sample_rate: int = 44_100,
        output_level: int = 25,
    ) -> None:
        self.device = device
        self.sample_rate = sample_rate
        self.output_level = max(0, min(100, int(output_level)))
        self._process = None
        self._cancel = None
        self._events = None
        self._level = None

    @property
    def active(self) -> bool:
        return self._process is not None and self._process.is_alive()

    def set_output_level(self, level: int) -> None:
        self.output_level = max(0, min(100, int(level)))
        if self._level is not None:
            self._level.value = self.output_level

    def play(self, path: str | Path) -> None:
        self.stop()
        tape_path = Path(path)
        start_event_index = selected_event_index(tape_path)
        context = multiprocessing.get_context("spawn")
        self._cancel = context.Event()
        self._events = context.Queue()
        self._level = context.Value("i", self.output_level, lock=False)
        self._process = context.Process(
            target=_play_worker,
            args=(
                str(tape_path),
                self.device,
                self.sample_rate,
                start_event_index,
                self._cancel,
                self._events,
                self._level,
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
        self._level = None


def _play_worker(
    path,
    device,
    sample_rate,
    start_event_index,
    cancelled,
    events,
    output_level,
) -> None:
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
    duration_seconds = None
    try:
        tape_events = tuple(iter_tape_events(path))
        start_event_index = min(
            len(tape_events),
            max(0, int(start_event_index)),
        )
        total_samples = count_pcm_samples(
            tape_events,
            sample_rate=sample_rate,
        )
        base_samples = count_pcm_samples(
            tape_events[:start_event_index],
            sample_rate=sample_rate,
        )
        duration_seconds = total_samples / sample_rate

        remaining = tape_events[start_event_index:]
        stop_offset = next(
            (
                index
                for index, event in enumerate(remaining)
                if isinstance(event, TapeStop)
            ),
            None,
        )
        playback_events = (
            remaining[:stop_offset]
            if stop_offset is not None
            else remaining
        )

        player = subprocess.Popen(command, stdin=subprocess.PIPE)
        if player.stdin is None:
            raise RuntimeError("cannot open ALSA input pipe")
        events.put(
            PlaybackEvent(
                "started",
                position_seconds=base_samples / sample_rate,
                duration_seconds=duration_seconds,
            )
        )

        def report_phase_progress(samples: int, phase: str) -> None:
            events.put(
                PlaybackEvent(
                    "progress",
                    position_seconds=min(
                        duration_seconds,
                        (base_samples + samples) / sample_rate,
                    ),
                    duration_seconds=duration_seconds,
                    phase=phase if phase in {"pilot", "data", "pause"} else None,
                )
            )

        written_samples = write_pcm(
            playback_events,
            player.stdin,
            sample_rate=sample_rate,
            cancelled=cancelled.is_set,
            chunk_size=8_192,
            level_percent=lambda: output_level.value,
            phase_progress=report_phase_progress,
        )
        absolute_position = min(
            duration_seconds,
            (base_samples + written_samples) / sample_rate,
        )
        player.stdin.close()
        return_code = player.wait()
        if cancelled.is_set():
            events.put(
                PlaybackEvent(
                    "stopped",
                    position_seconds=absolute_position,
                    duration_seconds=duration_seconds,
                )
            )
        elif return_code:
            events.put(PlaybackEvent("error", f"ALSA EXIT {return_code}"))
        elif stop_offset is not None:
            events.put(
                PlaybackEvent(
                    "stopped",
                    message="TAPE STOP",
                    position_seconds=absolute_position,
                    duration_seconds=duration_seconds,
                )
            )
        else:
            events.put(
                PlaybackEvent(
                    "finished",
                    position_seconds=absolute_position,
                    duration_seconds=duration_seconds,
                )
            )
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

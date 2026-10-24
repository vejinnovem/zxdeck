"""Runtime touchscreen renderer state and device-only UI refinements."""

from __future__ import annotations

from .device_renderer import DeviceTouchRenderer as BaseDeviceTouchRenderer
from .renderer import (
    BLACK,
    CYAN,
    DARK,
    DIM,
    GREEN,
    RED,
    YELLOW,
    HitTarget,
    RenderedScreen,
    TAPE_TITLE_RECT,
)


SPECTRUM_BLUE = (0, 70, 235)
PROGRESS_INNER_RECT = (17, 83, 224, 92)


class DeviceTouchRenderer(BaseDeviceTouchRenderer):
    """Preserve marquee state and refine runtime-only file navigation."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._runtime_title_name: str | None = None
        self._runtime_title_offset = 0

    def render_tape_title(self, tape_name: str, *, offset: int = 0):
        if tape_name != self._runtime_title_name:
            self._runtime_title_name = tape_name
            self._runtime_title_offset = 0
        self._runtime_title_offset = max(0, int(offset))
        return super().render_tape_title(tape_name, offset=offset)

    def render_home(self, state):
        tape_name = state.tape_name or "NO TAPE"
        saved_offset = (
            self._runtime_title_offset
            if tape_name == self._runtime_title_name
            else 0
        )

        rendered = super().render_home(state)

        if saved_offset:
            title = super().render_tape_title(
                tape_name,
                offset=saved_offset,
            )
            rendered.image.paste(title, TAPE_TITLE_RECT[:2])

        self._runtime_title_name = tape_name
        self._runtime_title_offset = saved_offset
        return rendered

    def decorate_signal_progress(
        self,
        image,
        state,
        *,
        phase: str | None,
        animation_step: int = 0,
    ) -> None:
        """Paint Spectrum-like pilot/data stripes while preserving progress.

        The whole progress track identifies the current signal phase. Elapsed
        stripes are bright and the remaining part is dimmed, so phase remains
        visible even at the start of a tape while the bar still conveys time.
        """
        if phase not in {"pilot", "data"}:
            return

        from PIL import ImageDraw

        draw = ImageDraw.Draw(image)
        left, top, right, bottom = PROGRESS_INNER_RECT
        width = right - left
        ratio = 0.0
        if state.duration_seconds and state.duration_seconds > 0:
            ratio = min(1.0, max(0.0, state.position_seconds / state.duration_seconds))
        elapsed_right = left + int(width * ratio)

        bright = (RED, SPECTRUM_BLUE) if phase == "pilot" else (YELLOW, SPECTRUM_BLUE)
        dim = tuple(tuple(channel // 4 for channel in colour) for colour in bright)
        stripe_width = 8
        shift = (animation_step * 2) % (stripe_width * 2)

        x = left - shift
        stripe_index = 0
        while x < right:
            segment_left = max(left, x)
            segment_right = min(right, x + stripe_width)
            if segment_right > segment_left:
                colour_index = stripe_index % 2

                # A stripe can straddle the playhead.  Draw its elapsed and
                # remaining pieces separately so no bright pixels protrude
                # into the unplayed side merely because the stripe started on
                # the left of the progress boundary.
                bright_right = min(segment_right, elapsed_right)
                if bright_right > segment_left:
                    draw.rectangle(
                        (segment_left, top, bright_right - 1, bottom - 1),
                        fill=bright[colour_index],
                    )

                dim_left = max(segment_left, elapsed_right)
                if segment_right > dim_left:
                    draw.rectangle(
                        (dim_left, top, segment_right - 1, bottom - 1),
                        fill=dim[colour_index],
                    )
            x += stripe_width
            stripe_index += 1

        # A narrow marker keeps the exact progress position legible even when
        # the bright/dim boundary lands inside a coloured stripe.
        if left < elapsed_right < right:
            draw.line((elapsed_right, top, elapsed_right, bottom - 1), fill=(245, 245, 245))

    def render_files(
        self,
        files,
        *,
        selected: int = 0,
        offset: int = 0,
        query: str = "",
    ) -> RenderedScreen:
        title = "FILES" if not query else f"FILES:{query[:9]}"
        return self._render_file_list(
            title,
            files,
            selected=selected,
            offset=offset,
            open_prefix="open:",
            footer=(
                ("back", "BACK", CYAN),
                ("up", "UP", YELLOW),
                ("down", "DOWN", YELLOW),
                ("search", "FIND", GREEN),
            ),
        )

    def render_saves(
        self,
        files,
        *,
        selected: int = 0,
        offset: int = 0,
    ) -> RenderedScreen:
        return self._render_file_list(
            "SAVES",
            files,
            selected=selected,
            offset=offset,
            open_prefix="open-save:",
            footer=(
                ("back", "BACK", CYAN),
                ("save-up", "UP", YELLOW),
                ("save-down", "DOWN", YELLOW),
                ("saves-refresh", "REFRESH", GREEN),
            ),
            empty_message="NO SAVES YET",
        )

    def _render_file_list(
        self,
        title,
        files,
        *,
        selected,
        offset,
        open_prefix,
        footer,
        empty_message: str = "",
    ) -> RenderedScreen:
        image, draw = self._new_canvas()
        targets: list[HitTarget] = []
        self._header(draw, title, f"{len(files)}")

        visible = files[offset : offset + 6]
        row_top = 32
        row_height = 38
        if not visible and empty_message:
            self._center_text(draw, empty_message, 124, size=11, fill=DIM)

        for index, filename in enumerate(visible):
            absolute_index = offset + index
            rect = (
                8,
                row_top + index * row_height,
                232,
                row_top + index * row_height + 34,
            )
            if absolute_index == selected:
                draw.rectangle(rect, fill=(30, 60, 65), outline=CYAN)
            else:
                draw.rectangle(rect, fill=DARK, outline=(55, 55, 55))
            fitted = self._fit_text_to_width(
                draw,
                str(filename),
                max_width=210,
                size=10,
            )
            self._text(draw, fitted, (14, rect[1] + 10), size=10)
            targets.append(HitTarget(f"{open_prefix}{absolute_index}", rect))

        button_width = 60
        for index, (action, label, accent) in enumerate(footer):
            rect = (
                index * button_width,
                276,
                (index + 1) * button_width,
                320,
            )
            self._button(draw, rect, label, accent=accent, squared=True)
            targets.append(HitTarget(action, rect))
        return RenderedScreen(image, tuple(targets))

    def render_search(self, editor, *, cursor_visible: bool = True) -> RenderedScreen:
        rendered = super().render_search(editor, cursor_visible=cursor_visible)
        from PIL import ImageDraw

        draw = ImageDraw.Draw(rendered.image)
        draw.rectangle((0, 270, 240, 320), fill=BLACK)
        footer = (
            ("cancel", "CANCEL", RED),
            ("letters", "A-Z", YELLOW),
            ("saves", "SAVES", CYAN),
            ("apply-search", "FIND", GREEN),
        )
        targets = [
            target
            for target in rendered.targets
            if target.action not in {"cancel", "letters", "apply-search"}
        ]
        for index, (action, label, accent) in enumerate(footer):
            rect = (index * 60, 270, (index + 1) * 60, 320)
            self._button(draw, rect, label, accent=accent, squared=True)
            targets.append(HitTarget(action, rect))
        return RenderedScreen(rendered.image, tuple(targets))

    def _fit_text_to_width(self, draw, text: str, *, max_width: int, size: int) -> str:
        font = self._font(size)
        if self._text_width(draw, text, font) <= max_width:
            return text
        suffix = "..."
        suffix_width = self._text_width(draw, suffix, font)
        if suffix_width >= max_width:
            return suffix
        candidate = text
        while candidate:
            candidate = candidate[:-1]
            value = candidate + suffix
            if self._text_width(draw, value, font) <= max_width:
                return value
        return suffix

    @staticmethod
    def _text_width(draw, text: str, font) -> int:
        box = draw.textbbox((0, 0), text, font=font)
        return box[2] - box[0]

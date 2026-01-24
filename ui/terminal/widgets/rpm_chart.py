from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean
from typing import List, Sequence

from rich.box import ROUNDED
from rich.panel import Panel
from rich.style import Style
from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget


@dataclass(frozen=True)
class RPMSeries:
    title: str
    accent: str
    unit: str = "rpm"


class RPMChart(Widget):
    """A small terminal chart for a numeric time series (area + line, with axis labels)."""

    series: reactive[List[float]] = reactive(list)
    labels: reactive[List[str]] = reactive(list)
    subtitle_text: reactive[str | None] = reactive(None)
    meta: reactive[RPMSeries] = reactive(RPMSeries("RPM", "cyan"))

    def __init__(
        self,
        title: str,
        *,
        accent: str = "cyan",
        unit: str = "rpm",
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.meta = RPMSeries(title=title, accent=accent, unit=unit)

    def set_series(
        self,
        values: Sequence[float],
        *,
        labels: Sequence[str] | None = None,
        subtitle: str | None = None,
    ) -> None:
        self.series = list(values)
        if labels is not None:
            self.labels = list(labels)
        self.subtitle_text = subtitle
        self.refresh()

    def push(self, value: float) -> None:
        values = list(self.series)
        values.append(float(value))
        self.series = values
        self.refresh()

    def _sample(self, values: Sequence[float], width: int) -> List[float]:
        if width <= 0:
            return []
        if not values:
            return [0.0] * width
        if len(values) >= width:
            return list(values[-width:])
        return [0.0] * (width - len(values)) + list(values)

    def _sample_labels(self, labels: Sequence[str], width: int) -> List[str]:
        if width <= 0:
            return []
        if not labels:
            return [""] * width
        if len(labels) >= width:
            return list(labels[-width:])
        return [""] * (width - len(labels)) + list(labels)

    def _format_compact(self, value: float) -> str:
        if value >= 1000:
            return f"{value/1000:.1f}k"
        return f"{value:.0f}"

    def _format_time_range(self, labels: Sequence[str], chart_width: int, axis_width: int, accent: str = "cyan") -> Text | None:
        # Find first and last non-empty labels
        start_index = next((idx for idx, label in enumerate(labels) if label), None)
        end_index = next((idx for idx in range(len(labels) - 1, -1, -1) if labels[idx]), None)

        start = labels[start_index] if start_index is not None else ""
        end = labels[end_index] if end_index is not None else ""

        if not start and not end:
            return None

        time_style = Style(color=accent)
        baseline = [" "] * chart_width

        # Place start label at the left (position 0)
        if start:
            for idx, ch in enumerate(start):
                if idx < chart_width:
                    baseline[idx] = ch

        # Place end label at the right edge
        if end and end != start:
            end_pos = max(0, chart_width - len(end))
            # Don't overlap with start label
            if end_pos < len(start) + 2:
                end_pos = len(start) + 2
            if end_pos + len(end) <= chart_width:
                for idx, ch in enumerate(end):
                    pos = end_pos + idx
                    if pos < chart_width:
                        baseline[pos] = ch

        # If only one label, show it on the right as "now"
        if start == end and start:
            # Clear baseline and place single label at right
            baseline = [" "] * chart_width
            end_pos = max(0, chart_width - len(start))
            for idx, ch in enumerate(start):
                pos = end_pos + idx
                if pos < chart_width:
                    baseline[pos] = ch

        line = Text(" " * axis_width, style=time_style)
        line.append("".join(baseline), style=time_style)
        return line

    def render(self) -> Panel:
        width = max(12, self.size.width)
        height = max(6, self.size.height)

        inner_width = max(8, width - 2)
        inner_height = max(3, height - 2)

        axis_width = 6
        chart_width = max(6, inner_width - axis_width - 1)

        sampled_labels = self._sample_labels(self.labels, chart_width)
        time_footer = self._format_time_range(sampled_labels, chart_width=chart_width, axis_width=axis_width, accent=self.meta.accent)

        # Account for x-axis line + time labels + stats footer
        footer_lines = 2 + (1 if time_footer else 0)
        chart_height = max(3, inner_height - footer_lines)

        samples = self._sample(self.series, chart_width)
        max_value = max(samples) if samples else 0.0
        max_value = max(max_value, 1.0)

        current = samples[-1] if samples else 0.0
        min_value = min(samples) if samples else 0.0
        avg_value = fmean(samples) if samples else 0.0

        accent_style = Style(color=self.meta.accent, bold=True)
        grid_style = Style(color="bright_black")
        axis_style = Style(color="bright_black", bold=True)

        mid_row = chart_height // 2

        lines: List[Text] = []
        for row in range(chart_height):
            label_value = max_value * (chart_height - 1 - row) / max(1, (chart_height - 1))
            show_label = row in (0, mid_row, chart_height - 1)
            label = self._format_compact(label_value).rjust(axis_width - 1) if show_label else " " * (axis_width - 1)
            line = Text(label, style=axis_style)
            line.append("│", style=axis_style)

            for col, value in enumerate(samples):
                level = 0.0 if max_value <= 0 else value / max_value
                y = int(round((1.0 - level) * (chart_height - 1)))

                # Only show dot when value > 0
                if row == y and value > 0:
                    line.append("●", style=accent_style)
                elif row == mid_row:
                    line.append("·", style=grid_style)
                else:
                    line.append(" ", style=grid_style)

            lines.append(line)

        # Create X-axis line
        x_axis_line = Text(" " * (axis_width - 1), style=axis_style)
        x_axis_line.append("└", style=axis_style)
        x_axis_line.append("─" * chart_width, style=axis_style)

        max_sample = max(samples) if samples else 0.0
        is_int_series = all(abs(value - round(value)) < 1e-9 for value in samples) if samples else True
        if is_int_series:
            footer_text = f"min {int(min_value)}  avg {avg_value:.1f}  max {int(max_sample)}"
        else:
            footer_text = f"min {min_value:.1f}  avg {avg_value:.1f}  max {max_sample:.1f}"

        footer = Text(footer_text, style=Style(color="bright_black"), no_wrap=True)

        body_parts: List[Text] = [*lines]
        body_parts.append(x_axis_line)
        if time_footer:
            body_parts.append(time_footer)
        body_parts.append(footer)
        body = Text("\n").join(body_parts)

        subtitle_value = self.subtitle_text or f"{current:,.1f} {self.meta.unit}"
        subtitle = Text(subtitle_value, style=accent_style)

        return Panel(
            body,
            title=Text(self.meta.title, style=accent_style),
            subtitle=subtitle,
            subtitle_align="right",
            padding=(0, 1),
            box=ROUNDED,
            border_style=Style(color=self.meta.accent),
        )

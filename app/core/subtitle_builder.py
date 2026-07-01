from __future__ import annotations

import re
from difflib import SequenceMatcher

try:
    from rapidfuzz.fuzz import ratio as rapid_ratio
except Exception:  # pragma: no cover - optional speed dependency
    rapid_ratio = None

from app.models.settings import MergeSettings
from app.models.subtitle import OcrSample, SubtitleSegment


NOISE_RE = re.compile(r"^[\W_]+$", re.UNICODE)


def normalize_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if rapid_ratio:
        return rapid_ratio(a, b) / 100.0
    return SequenceMatcher(None, a, b).ratio()


class SubtitleBuilder:
    def __init__(self, merge_settings: MergeSettings, confidence_threshold: float, frame_step: float):
        self.merge_settings = merge_settings
        self.confidence_threshold = confidence_threshold
        self.frame_step = max(0.1, frame_step)

    def build(self, samples: list[OcrSample]) -> list[SubtitleSegment]:
        segments: list[SubtitleSegment] = []
        current: SubtitleSegment | None = None
        blank_since: float | None = None

        for sample in sorted(samples, key=lambda item: item.time):
            text = normalize_text(sample.text)
            if sample.confidence < self.confidence_threshold or not text or NOISE_RE.match(text):
                if current and blank_since is None:
                    blank_since = sample.time
                if current and blank_since is not None:
                    gap = sample.time - blank_since
                    if gap > self.merge_settings.max_blank_gap_seconds:
                        segments.append(current)
                        current = None
                        blank_since = None
                continue

            blank_since = None
            if current is None:
                current = SubtitleSegment(
                    index=0,
                    start=sample.time,
                    end=sample.time + self.frame_step,
                    text=text,
                    confidence=sample.confidence,
                )
                continue

            score = similarity(current.text, text)
            if score >= self.merge_settings.duplicate_similarity:
                current.end = sample.time + self.frame_step
                current.confidence = max(current.confidence, sample.confidence)
                if len(text) > len(current.text):
                    current.text = text
            else:
                segments.append(current)
                current = SubtitleSegment(
                    index=0,
                    start=sample.time,
                    end=sample.time + self.frame_step,
                    text=text,
                    confidence=sample.confidence,
                )

        if current:
            segments.append(current)

        for index, segment in enumerate(segments, start=1):
            segment.index = index
            if segment.end <= segment.start:
                segment.end = segment.start + self.frame_step
        return segments

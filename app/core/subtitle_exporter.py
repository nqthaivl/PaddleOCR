from __future__ import annotations

from pathlib import Path

from app.models.subtitle import SubtitleSegment


def format_srt_time(seconds: float) -> str:
    millis = int(round(max(0.0, seconds) * 1000))
    hours, remainder = divmod(millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def format_vtt_time(seconds: float) -> str:
    return format_srt_time(seconds).replace(",", ".")


def export_subtitles(path: str, fmt: str, segments: list[SubtitleSegment]) -> None:
    fmt = fmt.upper()
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "SRT":
        output.write_text(to_srt(segments), encoding="utf-8-sig")
    elif fmt == "VTT":
        output.write_text(to_vtt(segments), encoding="utf-8")
    elif fmt == "ASS":
        output.write_text(to_ass(segments), encoding="utf-8-sig")
    elif fmt == "TXT":
        output.write_text(to_txt(segments), encoding="utf-8")
    else:
        raise ValueError(f"Định dạng phụ đề chưa hỗ trợ: {fmt}")


def to_srt(segments: list[SubtitleSegment]) -> str:
    blocks = []
    for segment in segments:
        blocks.append(
            f"{segment.index}\n"
            f"{format_srt_time(segment.start)} --> {format_srt_time(segment.end)}\n"
            f"{segment.text}"
        )
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def to_vtt(segments: list[SubtitleSegment]) -> str:
    blocks = ["WEBVTT\n"]
    for segment in segments:
        blocks.append(
            f"{format_vtt_time(segment.start)} --> {format_vtt_time(segment.end)}\n"
            f"{segment.text}"
        )
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def to_txt(segments: list[SubtitleSegment]) -> str:
    return "\n".join(segment.text for segment in segments) + ("\n" if segments else "")


def to_ass(segments: list[SubtitleSegment]) -> str:
    header = """[Script Info]
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Microsoft YaHei,42,&H00FFFFFF,&H000000FF,&H00202020,&H7F000000,0,0,0,0,100,100,0,0,1,2,1,2,40,40,42,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header.rstrip()]
    for segment in segments:
        text = segment.text.replace("\n", r"\N")
        lines.append(
            "Dialogue: 0,"
            f"{format_ass_time(segment.start)},"
            f"{format_ass_time(segment.end)},"
            f"Default,,0,0,0,,{text}"
        )
    return "\n".join(lines) + "\n"


def format_ass_time(seconds: float) -> str:
    centis = int(round(max(0.0, seconds) * 100))
    hours, remainder = divmod(centis, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    secs, centis = divmod(remainder, 100)
    return f"{hours:d}:{minutes:02d}:{secs:02d}.{centis:02d}"


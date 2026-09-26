def apply_level_progress(current_progress: float, delta: float) -> tuple[float, int]:
    progress = current_progress + delta

    if progress >= 100:
        return 0.0, 1

    if progress < 0:
        return 0.0, 0

    return progress, 0


def level_progress_bar(progress: float, segments: int = 10) -> str:
    clamped = max(0.0, min(100.0, progress))
    filled = min(segments, int(round(clamped / 100 * segments)))
    return "⬆️" + "◾️" * filled + "▫️" * (segments - filled)

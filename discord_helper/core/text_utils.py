"""Utilities for preparing model output for voice delivery."""

import re


def sanitize_for_tts(text: str) -> str:
    """Return plain prose suitable for TTS playback.

    Local LLMs frequently produce Markdown, URLs, list markers and emoji even when
    instructed not to. This function acts as a final safety layer before TTS.
    """

    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"[*_#~]+", "", text)
    text = re.sub(r"[\U00010000-\U0010ffff]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    return text.strip()

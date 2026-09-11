"""Telegram chat ID normalization (legacy vs full channel form)."""


def alternate_chat_id(chat_id: int) -> int | None:
    """Return the alternate format for a Telegram chat ID (legacy vs full channel).

    Channels use -100xxxxxxxxxx, legacy groups use -xxxxxxxxx. Both refer to the same chat.
    """
    if chat_id >= 0:
        return None
    if chat_id <= -1000000000000:
        return chat_id + 1000000000000  # full -> legacy
    return chat_id - 1000000000000  # legacy -> full

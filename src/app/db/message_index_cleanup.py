"""Cleanup for dest_message_index (reply-threading map)."""

from __future__ import annotations

import logging

from app.db.gateway import DbConnection
from app.telegram.chat_ids import alternate_chat_id

logger = logging.getLogger(__name__)


def _source_variants(source_chat_id: int) -> list[int]:
    variants = [source_chat_id]
    alt = alternate_chat_id(source_chat_id)
    if alt is not None and alt not in variants:
        variants.append(alt)
    return variants


async def delete_dest_message_index_for_mapping(
    db: DbConnection,
    user_id: int,
    source_chat_id: int,
    dest_chat_id: int,
) -> int:
    """Remove all index rows for this mapping triple (both source ID forms). Returns deleted row count."""
    sources = _source_variants(source_chat_id)
    placeholders = ",".join("?" * len(sources))
    sql = (
        f"DELETE FROM dest_message_index WHERE user_id = ? AND dest_chat_id = ? "
        f"AND source_chat_id IN ({placeholders})"
    )
    params = [user_id, dest_chat_id, *sources]
    cur = await db.execute(sql, params)
    return cur.rowcount if cur.rowcount is not None else 0


async def purge_orphan_dest_message_index(
    db: DbConnection, *, dry_run: bool = False
) -> int:
    """Delete index rows that do not match any channel_mappings (user, source variant, dest).

    Uses batched per-user reads so alternate source IDs stay aligned with handlers.
    If dry_run is True, returns the count that would be removed without deleting.
    """
    async with db.execute("SELECT DISTINCT user_id FROM dest_message_index") as cur:
        user_rows = await cur.fetchall()
    user_ids = [int(r[0]) for r in user_rows]
    deleted_total = 0
    for uid in user_ids:
        async with db.execute(
            "SELECT source_chat_id, dest_chat_id FROM channel_mappings WHERE user_id = ?",
            (uid,),
        ) as cur:
            mapping_rows = await cur.fetchall()
        valid_pairs: set[tuple[int, int]] = set()
        for s, d in mapping_rows:
            for src in _source_variants(int(s)):
                valid_pairs.add((src, int(d)))
        async with db.execute(
            "SELECT user_id, source_chat_id, source_msg_id, dest_chat_id "
            "FROM dest_message_index WHERE user_id = ?",
            (uid,),
        ) as cur:
            index_rows = await cur.fetchall()
        for u, src, smid, dst in index_rows:
            if (int(src), int(dst)) not in valid_pairs:
                deleted_total += 1
                if not dry_run:
                    await db.execute(
                        "DELETE FROM dest_message_index WHERE user_id = ? AND source_chat_id = ? "
                        "AND source_msg_id = ? AND dest_chat_id = ?",
                        (int(u), int(src), int(smid), int(dst)),
                    )
    if deleted_total and not dry_run:
        await db.commit()
        logger.info("Purged %d orphan dest_message_index row(s)", deleted_total)
    return deleted_total

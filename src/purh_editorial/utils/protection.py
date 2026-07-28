"""Conservative protected-zone checks shared by editorial services."""

from __future__ import annotations

from typing import Any


_PROTECTED_BLOCK_TYPES = {
    "quote_block", "lineated_block", "bibliography_item", "code", "table", "formula",
}


def _attributes_mark_protected(attributes: dict[str, Any] | None) -> bool:
    if not attributes:
        return False
    if attributes.get("protected") is True or attributes.get("is_protected") is True:
        return True
    return bool(str(attributes.get("protected_zone", "")).strip())


def is_protected_inline(inline: Any) -> bool:
    return _attributes_mark_protected(getattr(inline, "attributes", None))


def is_protected_block(block: Any) -> bool:
    if getattr(block, "block_type", "") in _PROTECTED_BLOCK_TYPES:
        return True
    if _attributes_mark_protected(getattr(block, "attributes", None)):
        return True
    return any(is_protected_inline(inline) for inline in getattr(block, "inlines", []))


def is_protected_note(note: Any, *, protected_target_refs: set[str] | None = None) -> bool:
    if _attributes_mark_protected(getattr(note, "attributes", None)):
        return True
    if any(is_protected_inline(inline) for inline in getattr(note, "inlines", [])):
        return True
    return bool(protected_target_refs and getattr(note, "target_ref", None) in protected_target_refs)

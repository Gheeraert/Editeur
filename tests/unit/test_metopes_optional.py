from __future__ import annotations

from purh_editorial.model import Block, Document
from purh_editorial.services.metopes_mapper import MetopesMapper


def _block(block_id: str, role: str, **semantic: object) -> Block:
    return Block(block_id, "paragraph", attributes={"semantic": {"role": role, **semantic}})


def test_mapper_uses_canonical_roles_and_not_text() -> None:
    document = Document(
        "doc", "source", "txt",
        blocks=[
            _block("abstract", "abstract"),
            _block("keywords", "keywords"),
            _block("thanks", "acknowledgment"),
            Block("ordinary", "paragraph", text="Résumé : ce paragraphe reste ordinaire.", attributes={"semantic": {"role": "paragraph"}}),
            Block("unknown", "paragraph", text="Mots-clés", attributes={}),
        ],
    )
    mapped, transformations = MetopesMapper().apply(document)

    assert mapped.blocks[0].attributes["metopes_style"] == "TEI_abstract"
    assert mapped.blocks[1].attributes["metopes_style"] == "TEI_keywords"
    assert mapped.blocks[2].attributes["metopes_style"] == "TEI_acknowledgment"
    assert mapped.blocks[3].attributes["metopes_style"] == "Normal"
    assert "metopes_style" not in mapped.blocks[4].attributes
    assert all(item.operation == "assign_metopes_style" for item in transformations)

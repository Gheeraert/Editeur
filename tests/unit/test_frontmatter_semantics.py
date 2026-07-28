from purh_editorial.model import Document, Paragraph
from purh_editorial.model.semantics import read_block_semantics
from purh_editorial.services.pivot_canonicalizer import PivotCanonicalizer
from purh_editorial.services.structure_service import StructurePreparationService


def test_structure_recognizes_frontmatter_before_mapping_and_canonicalizer_preserves_it() -> None:
    document = Document("doc", "source", "txt", blocks=[Paragraph("a", text="Abstract:"), Paragraph("k", text="Keywords:"), Paragraph("r", text="Acknowledgments")])
    _diagnostics, transformations = StructurePreparationService().process(document)
    PivotCanonicalizer().apply(document)
    assert [read_block_semantics(block).role for block in document.blocks] == ["abstract", "keywords", "acknowledgment"]
    assert {item.rule_id for item in transformations} == {"structure.frontmatter.abstract", "structure.frontmatter.keywords", "structure.frontmatter.acknowledgment"}


def test_frontmatter_recognition_is_idempotent_and_preserves_existing_roles() -> None:
    document = Document("doc", "source", "txt", blocks=[
        Paragraph("abstract", text="Abstract:"),
        Paragraph("conflict", text="Résumé :", attributes={"semantic": {"role": "keywords"}}),
    ])
    _diagnostics, first = StructurePreparationService().process(document)
    diagnostics, second = StructurePreparationService().process(document)

    assert first[0].before is None
    assert second == []
    assert read_block_semantics(document.blocks[0]).role == "abstract"
    assert read_block_semantics(document.blocks[1]).role == "keywords"
    assert any(diag.status == "pending_human_review" for diag in diagnostics)


def test_frontmatter_match_stops_heading_heuristics_without_rewriting_role() -> None:
    document = Document("doc", "source", "txt", blocks=[
        Paragraph("abstract", text="Abstract:", attributes={"semantic": {"role": "abstract"}, "all_caps": True}),
        Paragraph("conflict", text="Résumé :", attributes={"semantic": {"role": "keywords"}, "all_caps": True}),
    ])
    diagnostics, transformations = StructurePreparationService().process(document)
    _diagnostics_second, transformations_second = StructurePreparationService().process(document)

    assert transformations == []
    assert transformations_second == []
    assert [block.block_type for block in document.blocks] == ["paragraph", "paragraph"]
    assert [read_block_semantics(block).role for block in document.blocks] == ["abstract", "keywords"]
    assert any(diag.category == "frontmatter_role_conflict" for diag in diagnostics)

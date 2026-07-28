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

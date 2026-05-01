from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Document, Paragraph
from purh_editorial.services.orthotypo_service import NBSP, NNBSP, OrthotypoService


def _apply_orthotypo(text: str) -> str:
    document = Document(
        document_id="doc-orthotypo",
        source_path="tests/fixtures/minimal_source.txt",
        source_format="txt",
        blocks=[Paragraph(block_id="p1", text=text)],
    )
    service = OrthotypoService()
    corrected, _transformations = service.apply(document)
    return corrected.blocks[0].text


class OrthotypoServiceGuardrailsTests(unittest.TestCase):
    def test_r_sp_001_simple_cases(self) -> None:
        self.assertEqual(_apply_orthotypo("Voici: un cas"), f"Voici{NNBSP}: un cas")
        self.assertEqual(_apply_orthotypo("Pourquoi?"), f"Pourquoi{NNBSP}?")

    def test_r_sp_001_does_not_change_technical_tokens(self) -> None:
        self.assertEqual(_apply_orthotypo("http://exemple.org:8080/test"), "http://exemple.org:8080/test")
        self.assertEqual(_apply_orthotypo("https://exemple.org/a:b"), "https://exemple.org/a:b")
        self.assertEqual(_apply_orthotypo("10:30"), "10:30")
        self.assertEqual(_apply_orthotypo("1:2"), "1:2")
        self.assertEqual(_apply_orthotypo("format 16:9"), "format 16:9")
        self.assertEqual(_apply_orthotypo(r"C:\dossier\fichier"), r"C:\dossier\fichier")
        self.assertEqual(_apply_orthotypo("RFC 1234:5"), "RFC 1234:5")

    def test_r_sp_002_space_before_comma_or_dot(self) -> None:
        self.assertEqual(_apply_orthotypo("mot , suite"), "mot, suite")
        self.assertEqual(_apply_orthotypo("mot . Suite"), "mot. Suite")
        self.assertEqual(_apply_orthotypo("Attends… , oui"), "Attends…, oui")

    def test_r_sp_003_reduce_double_spaces_only(self) -> None:
        self.assertEqual(_apply_orthotypo("mot  mot"), "mot mot")
        self.assertEqual(_apply_orthotypo("mot \t mot"), "mot mot")
        self.assertEqual(_apply_orthotypo(f"mot{NBSP}mot"), f"mot{NBSP}mot")
        self.assertEqual(_apply_orthotypo(f"mot{NNBSP}mot"), f"mot{NNBSP}mot")

    def test_r_ab_001_etc_variants(self) -> None:
        self.assertEqual(_apply_orthotypo("etc..."), "etc.")
        self.assertEqual(_apply_orthotypo("etc…"), "etc.")
        self.assertEqual(_apply_orthotypo("etc...."), "etc.")

    def test_guillemets_droits_cas_simple(self) -> None:
        self.assertEqual(_apply_orthotypo('Il dit "bonjour".'), f"Il dit «{NNBSP}bonjour{NNBSP}».")

    def test_guillemets_second_niveau_dans_guillemets_francais(self) -> None:
        self.assertEqual(
            _apply_orthotypo('« Il dit "bonjour" puis se tut. »'),
            f"«{NNBSP}Il dit “bonjour” puis se tut.{NNBSP}»",
        )

    def test_guillemets_second_niveau_deja_typographiques_reste_inchange(self) -> None:
        text = "« Il dit “bonjour” puis se tut. »"
        self.assertEqual(_apply_orthotypo(text), f"«{NNBSP}Il dit “bonjour” puis se tut.{NNBSP}»")

    def test_guillemets_second_niveau_sans_espaces_internes(self) -> None:
        result = _apply_orthotypo('« "bonjour" »')
        self.assertIn("“bonjour”", result)
        self.assertNotIn(f"“{NNBSP}", result)
        self.assertNotIn(f"{NNBSP}”", result)

    def test_guillemets_droits_contextes_techniques_inchanges(self) -> None:
        self.assertEqual(_apply_orthotypo('print("hello")'), 'print("hello")')
        self.assertEqual(_apply_orthotypo('class="note"'), 'class="note"')
        self.assertEqual(_apply_orthotypo('<hi rend="italic">'), '<hi rend="italic">')
        self.assertEqual(_apply_orthotypo('data-value="x"'), 'data-value="x"')

    def test_guillemets_anglais_typographiques_suivent_la_meme_chaine(self) -> None:
        self.assertEqual(
            _apply_orthotypo("\u201cD\u2019une secr\u00e8te horreur je me sens frissonner.\u201d"),
            f"\u00ab{NNBSP}D\u2019une secr\u00e8te horreur je me sens frissonner.{NNBSP}\u00bb",
        )

    def test_r_ortho_ligature_oe_001(self) -> None:
        self.assertEqual(_apply_orthotypo("boeuf boeufs oeuf oeufs"), "bœuf bœufs œuf œufs")
        self.assertEqual(_apply_orthotypo("soeur soeurs coeur coeurs"), "sœur sœurs cœur cœurs")
        self.assertEqual(_apply_orthotypo("oeuvre oeuvres oeil"), "œuvre œuvres œil")
        self.assertEqual(_apply_orthotypo("voeu voeux noeud noeuds moeurs"), "vœu vœux nœud nœuds mœurs")
        self.assertEqual(_apply_orthotypo("Boeuf Oeuvre"), "Bœuf Œuvre")

    def test_ligature_oe_ne_remplace_pas_hors_table(self) -> None:
        self.assertEqual(_apply_orthotypo("coelacanthe"), "coelacanthe")

    def test_r_sp_004_thousands_separator(self) -> None:
        self.assertEqual(_apply_orthotypo("1 000"), f"1{NNBSP}000")
        self.assertEqual(_apply_orthotypo("10 000"), f"10{NNBSP}000")
        self.assertEqual(_apply_orthotypo("1 500 000"), f"1{NNBSP}500{NNBSP}000")
        self.assertEqual(_apply_orthotypo("12 345 678"), f"12{NNBSP}345{NNBSP}678")

    def test_r_sp_004_guardrails(self) -> None:
        self.assertEqual(_apply_orthotypo("en 2025"), "en 2025")
        self.assertEqual(_apply_orthotypo("ISBN 978 2 1234 5678 9"), "ISBN 978 2 1234 5678 9")
        self.assertEqual(_apply_orthotypo(f"1{NNBSP}000"), f"1{NNBSP}000")

    def test_r_so_002_ordinaux_simples(self) -> None:
        self.assertEqual(_apply_orthotypo("la 1ère partie"), "la 1re partie")
        self.assertEqual(_apply_orthotypo("la 1ere partie"), "la 1re partie")
        self.assertEqual(_apply_orthotypo("le 1er chapitre"), "le 1er chapitre")
        self.assertEqual(_apply_orthotypo("la 2ème partie"), "la 2e partie")
        self.assertEqual(_apply_orthotypo("le 5ème chapitre"), "le 5e chapitre")
        self.assertEqual(_apply_orthotypo("le 5eme chapitre"), "le 5e chapitre")

    def test_r_so_002_guardrails(self) -> None:
        self.assertEqual(_apply_orthotypo("version 2.0"), "version 2.0")
        self.assertEqual(_apply_orthotypo("5e chapitre"), "5e chapitre")


if __name__ == "__main__":
    unittest.main()

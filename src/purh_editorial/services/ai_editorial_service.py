from __future__ import annotations

import json
import re
import copy
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from purh_editorial.model import Document, InlineSpan, Transformation
from purh_editorial.services.orthotypo_service import COLOR_AI, _find_changed_regions
from purh_editorial.utils import make_id

# ── Prompt système — règles PURH explicites ───────────────────────────────────
_SYSTEM = """\
Tu es éditeur scientifique aux Presses universitaires de Rouen et du Havre (PURH).
Tu révises un manuscrit académique en français (SHS : histoire, littérature, linguistique).

RÈGLES ORTHOTYPOGRAPHIQUES PURH À APPLIQUER :
- Guillemets français obligatoires : « texte » avec espaces insécables (jamais "texte")
- Apostrophe typographique ’ (jamais l'apostrophe droite ')
- Espace insécable avant : !, ?, ;, :
- Siècles en chiffres romains petites caps : xviiie siècle (jamais 18e siècle ou XVIIIe)
- Abréviations normalisées : p. XX (pas pp.), n° X (pas no.), art. cit., op. cit.
- Points de suspension : … (entité Unicode unique, jamais trois points séparés ...)
- Trait d'union vs tiret : tiret demi-cadratin – pour les incises (jamais tiret simple -)

RÈGLES STRICTES D'INTERVENTION :
- Tu ne réécris JAMAIS un paragraphe entier.
- Chaque correction est LOCALE : entre 2 et 12 mots maximum.
- Tu respectes absolument la voix et le style de l'auteur.
- Tu ne corriges PAS : les choix disciplinaires, archaïsmes savants, néologismes justifiés,
  citations, noms propres, termes techniques, latinismes.
- Tu n'interviens QUE sur ce qui est CLAIREMENT fautif :
  • guillemets droits au lieu de guillemets français,
  • apostrophe droite au lieu de typographique,
  • trois points séparés au lieu de …,
  • répétition immédiate du même mot dans la même phrase,
  • solécisme ou incohérence de registre évidente.
- Si aucune correction ne s'impose, retourne {"corrections": []}.
- Propose au maximum 2 corrections par passage.

Format de réponse (JSON strict, aucun texte autour) :
{"corrections": [{"original": "texte exact à remplacer", "corrected": "texte corrigé", "raison": "règle PURH concernée"}]}
"""

# Nombre maximum d'appels API par document
MAX_API_CALLS = 8

# Longueur minimale d'un paragraphe pour mériter une analyse IA
MIN_BLOCK_LENGTH = 200

# Nombre de paragraphes de contexte fournis à l'IA
_CONTEXT_WINDOW = 2


@dataclass
class AICorrection:
    original: str
    corrected: str
    raison: str


class AIEditorialService:
    """
    Applique des corrections éditoriales ciblées via LLM (très modérément).
    Chaque correction remplace 2-12 mots et est surlignée en rose.
    """

    module_name = "ai_editorial"
    color = COLOR_AI

    def __init__(self, api_key: str | None, model: str, base_url: str, timeout: int = 25) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def apply(
        self,
        document: Document,
        max_calls: int = MAX_API_CALLS,
    ) -> tuple[Document, list[Transformation]]:
        if not self.available:
            return document, []

        doc = copy.deepcopy(document)
        transformations: list[Transformation] = []
        calls_used = 0

        # Sélection des blocs candidats (paragraphes longs du corps)
        candidates = [
            (i, b) for i, b in enumerate(doc.blocks)
            if b.block_type == "paragraph"
            and len(b.text.strip()) >= MIN_BLOCK_LENGTH
        ]

        for idx, block in candidates:
            if calls_used >= max_calls:
                break

            context_before = _extract_context(doc.blocks, idx, window=_CONTEXT_WINDOW, before=True)
            context_after = _extract_context(doc.blocks, idx, window=_CONTEXT_WINDOW, before=False)

            try:
                corrections = self._call_api(
                    block.text,
                    context_before=context_before,
                    context_after=context_after,
                )
                calls_used += 1
            except Exception:
                continue

            for corr in corrections:
                if not corr.original or not corr.corrected:
                    continue
                if corr.original == corr.corrected:
                    continue
                if corr.original not in block.text:
                    continue
                original_text = block.text
                corrected_text = block.text.replace(corr.original, corr.corrected, 1)
                if corrected_text == original_text:
                    continue
                regions = _find_changed_regions(original_text, corrected_text)
                if block.inlines:
                    from purh_editorial.services.orthotypo_service import (
                        OrthotypoService,
                    )
                    new_inlines = OrthotypoService._rebuild_inlines(
                        block.inlines, original_text, corrected_text, regions
                    )
                    for span in new_inlines:
                        if span.attributes.get("highlight_color") == "orthotypo":
                            span.attributes["highlight_color"] = self.color
                    block.inlines = new_inlines
                else:
                    block.attributes["highlight_color"] = self.color
                block.text = corrected_text
                transformations.append(Transformation(
                    transformation_id=make_id("tr"),
                    module=self.module_name,
                    target_ref=block.block_id,
                    operation="ai_correction",
                    before=original_text,
                    after=corrected_text,
                    rule_id="purh.ai.editorial",
                    applied=True,
                    attributes={
                        "raison": corr.raison,
                        "original_phrase": corr.original,
                        "corrected_phrase": corr.corrected,
                        "color": self.color,
                        "model": self.model,
                    },
                ))

        if transformations:
            doc.history.append(
                f"{self.module_name}: {len(transformations)} correction(s) IA appliquée(s) "
                f"({calls_used} appel(s) API)."
            )
        return doc, transformations

    # ── Appel API ─────────────────────────────────────────────────────────────

    def _call_api(
        self,
        text: str,
        *,
        context_before: str = "",
        context_after: str = "",
    ) -> list[AICorrection]:
        # Construire le message utilisateur avec contexte optionnel
        parts: list[str] = []
        if context_before:
            parts.append(f"[Contexte précédent]\n{context_before}\n")
        parts.append(f"[Passage à analyser]\n{text[:1400]}")
        if context_after:
            parts.append(f"\n[Contexte suivant]\n{context_after}")
        parts.append(
            "\n\nAnalyse ce passage et propose au plus 2 corrections locales "
            "(2-12 mots chacune, règles PURH). "
            "Si rien ne s'impose, retourne {\"corrections\": []}."
        )
        user_content = "\n".join(parts)

        payload = {
            "model": self.model,
            "temperature": 0.05,
            "max_tokens": 500,
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": user_content},
            ],
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "purh-editorial/2.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Groq HTTP {exc.code}: {detail[:200]}") from exc
        except Exception as exc:
            raise RuntimeError(f"API error: {exc}") from exc

        content = (
            body.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        return self._parse_corrections(content)

    # ── Parsing ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_corrections(content: str) -> list[AICorrection]:
        text = content.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text).strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if not m:
                return []
            try:
                data = json.loads(m.group(0))
            except json.JSONDecodeError:
                return []

        items = data.get("corrections", [])
        if not isinstance(items, list):
            return []

        result: list[AICorrection] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            orig = str(item.get("original", "")).strip()
            corr = str(item.get("corrected", "")).strip()
            raison = str(item.get("raison", "")).strip()
            if orig and corr and orig != corr:
                if len(orig.split()) <= 15 and len(corr.split()) <= 15:
                    result.append(AICorrection(original=orig, corrected=corr, raison=raison))
        return result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_context(blocks: list, idx: int, *, window: int, before: bool) -> str:
    """Extrait les `window` paragraphes avant ou après idx, concaténés."""
    if before:
        chunk = blocks[max(0, idx - window):idx]
    else:
        chunk = blocks[idx + 1:idx + 1 + window]
    texts = [b.text.strip()[:250] for b in chunk if b.text.strip()]
    return " / ".join(texts)

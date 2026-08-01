from __future__ import annotations

from unittest.mock import patch

import pytest

from purh_editorial.corrector.ai import GeminiAIClient, GroqAIClient, OllamaAIClient
from purh_editorial.corrector.gui import CorrectorApp


@pytest.fixture(scope="module")
def app():
    # Un seul Tk() root pour tout le module : en creer et en detruire un par
    # test declenche une instabilite connue de Tkinter (TclError
    # "tcl_findLibrary" sur une instanciation ulterieure dans le meme
    # process). L'etat (StringVar) est reinitialise manuellement entre
    # chaque test au lieu de recreer la fenetre.
    application = CorrectorApp()
    yield application
    application.destroy()


@pytest.fixture(autouse=True)
def _reset_ai_state(app: CorrectorApp):
    app._ai_mode.set("")
    app._ollama_model.set("")
    app._remote_provider.set("")
    app._api_key.set("")
    app._ollama_models_loaded = False
    app._ollama_model_entry.configure(values=())
    app.update()
    yield


def test_no_mode_selected_raises_error(app: CorrectorApp) -> None:
    with pytest.raises(ValueError, match="Choisissez un mode"):
        app._build_ai_client()


def test_disabled_mode_returns_none(app: CorrectorApp) -> None:
    app._ai_mode.set("disabled")
    assert app._build_ai_client() is None


def test_local_mode_without_model_raises_error(app: CorrectorApp) -> None:
    # Aucun modele ne doit etre trouve/preselectionne pour ce cas : mocke la
    # decouverte Ollama (sinon un vrai serveur local avec un modele charge
    # rendrait ce test non representatif, cf. le nouveau prefill automatique).
    with (
        patch("purh_editorial.corrector.gui.list_ollama_models", return_value=[]),
        patch("purh_editorial.corrector.gui.active_ollama_model", return_value=None),
    ):
        app._ai_mode.set("local")
        app.update()
    with pytest.raises(ValueError, match="modèle"):
        app._build_ai_client()


def test_local_mode_with_model_returns_ollama_client(app: CorrectorApp) -> None:
    app._ai_mode.set("local")
    app._ollama_model.set("mistral-small3.2:latest")
    client = app._build_ai_client()
    assert isinstance(client, OllamaAIClient)


def test_remote_mode_without_provider_raises_error(app: CorrectorApp) -> None:
    app._ai_mode.set("remote")
    with pytest.raises(ValueError, match="fournisseur"):
        app._build_ai_client()


def test_remote_mode_without_api_key_raises_error(app: CorrectorApp) -> None:
    app._ai_mode.set("remote")
    app._remote_provider.set("gemini")
    with pytest.raises(ValueError, match="clé API"):
        app._build_ai_client()


def test_remote_mode_gemini_returns_gemini_client(app: CorrectorApp) -> None:
    app._ai_mode.set("remote")
    app._remote_provider.set("gemini")
    app._api_key.set("fake-key")
    client = app._build_ai_client()
    assert isinstance(client, GeminiAIClient)


def test_remote_mode_groq_returns_groq_client(app: CorrectorApp) -> None:
    app._ai_mode.set("remote")
    app._remote_provider.set("groq")
    app._api_key.set("fake-key")
    client = app._build_ai_client()
    assert isinstance(client, GroqAIClient)


def test_ollama_field_enabled_only_in_local_mode(app: CorrectorApp) -> None:
    app.update()
    assert str(app._ollama_model_entry.cget("state")) == "disabled"

    app._ai_mode.set("local")
    app.update()
    assert str(app._ollama_model_entry.cget("state")) == "normal"

    app._ai_mode.set("remote")
    app.update()
    assert str(app._ollama_model_entry.cget("state")) == "disabled"


def test_remote_fields_enabled_only_in_remote_mode(app: CorrectorApp) -> None:
    app.update()
    assert str(app._api_key_entry.cget("state")) == "disabled"

    app._ai_mode.set("remote")
    app.update()
    assert str(app._api_key_entry.cget("state")) == "normal"

    app._ai_mode.set("local")
    app.update()
    assert str(app._api_key_entry.cget("state")) == "disabled"


def test_selecting_provider_prefills_api_key_from_environment(
    app: CorrectorApp, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "env-gemini-key")
    app._remote_provider.set("gemini")
    app.update()
    assert app._api_key.get() == "env-gemini-key"


def test_prefill_does_not_overwrite_a_manually_entered_key(
    app: CorrectorApp, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "env-gemini-key")
    monkeypatch.setenv("GROQ_API_KEY", "env-groq-key")
    app._remote_provider.set("gemini")
    app.update()
    app._api_key.set("saisie-manuelle")
    app._remote_provider.set("groq")
    app.update()
    assert app._api_key.get() == "saisie-manuelle"


def test_prefill_does_nothing_when_environment_variable_is_absent(
    app: CorrectorApp, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    app._remote_provider.set("gemini")
    app.update()
    assert app._api_key.get() == ""


def test_selecting_local_mode_prefills_active_ollama_model(app: CorrectorApp) -> None:
    with (
        patch(
            "purh_editorial.corrector.gui.list_ollama_models",
            return_value=["llama3.1:8b", "mistral-small3.2:latest"],
        ),
        patch(
            "purh_editorial.corrector.gui.active_ollama_model",
            return_value="mistral-small3.2:latest",
        ),
    ):
        app._ai_mode.set("local")
        app.update()
    assert app._ollama_model.get() == "mistral-small3.2:latest"
    assert list(app._ollama_model_entry.cget("values")) == [
        "llama3.1:8b",
        "mistral-small3.2:latest",
    ]


def test_selecting_local_mode_falls_back_to_first_model_when_none_active(
    app: CorrectorApp,
) -> None:
    with (
        patch(
            "purh_editorial.corrector.gui.list_ollama_models",
            return_value=["llama3.1:8b"],
        ),
        patch("purh_editorial.corrector.gui.active_ollama_model", return_value=None),
    ):
        app._ai_mode.set("local")
        app.update()
    assert app._ollama_model.get() == "llama3.1:8b"


def test_selecting_local_mode_does_not_overwrite_prefilled_env_value(
    app: CorrectorApp,
) -> None:
    app._ollama_model.set("un-autre-modele")
    with (
        patch(
            "purh_editorial.corrector.gui.list_ollama_models",
            return_value=["mistral-small3.2:latest"],
        ),
        patch(
            "purh_editorial.corrector.gui.active_ollama_model",
            return_value="mistral-small3.2:latest",
        ),
    ):
        app._ai_mode.set("local")
        app.update()
    assert app._ollama_model.get() == "un-autre-modele"
    # La liste deroulante reste alimentee malgre tout.
    assert list(app._ollama_model_entry.cget("values")) == ["mistral-small3.2:latest"]


def test_refresh_button_requeries_models_on_demand(app: CorrectorApp) -> None:
    app._ai_mode.set("local")
    with (
        patch(
            "purh_editorial.corrector.gui.list_ollama_models",
            return_value=["nouveau-modele:latest"],
        ),
        patch(
            "purh_editorial.corrector.gui.active_ollama_model",
            return_value=None,
        ),
    ):
        app._refresh_ollama_models()
    assert "nouveau-modele:latest" in app._ollama_model_entry.cget("values")

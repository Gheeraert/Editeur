from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_importing_rules_package_has_no_heavy_or_ai_side_effects() -> None:
    code = """
import json
import sys
import purh_editorial.rules
forbidden = [
    name for name in sys.modules
    if name == "tkinter"
    or name.startswith("win32com")
    or "ai_editorial_service" in name
    or "structure_ai_arbitrator" in name
]
print(json.dumps(forbidden))
"""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == "[]"


def test_importing_rules_model_for_execution_hints_stays_isolated() -> None:
    code = """
import json
import sys
import purh_editorial.rules.model
forbidden = [
    name for name in sys.modules
    if name == "tkinter"
    or name.startswith("win32com")
    or "ai_editorial_service" in name
    or "structure_ai_arbitrator" in name
    or ".ui" in name
    or "word_" in name
]
print(json.dumps(forbidden))
"""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == "[]"


def test_importing_engine_and_thresholds_stays_isolated() -> None:
    code = """
import json
import sys
import purh_editorial.rules.engine
import purh_editorial.rules.thresholds
forbidden = [
    name for name in sys.modules
    if name == "tkinter"
    or name.startswith("win32com")
    or "ai_editorial_service" in name
    or "structure_ai_arbitrator" in name
    or ".ui" in name
    or "word_" in name
    or ".services." in name
    or ".pipeline." in name
    or name == "purh_editorial.rules.shadow"
]
print(json.dumps(forbidden))
"""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == "[]"


def test_importing_shadow_stays_isolated() -> None:
    code = """
import json
import sys
import purh_editorial.rules.shadow
forbidden = [
    name for name in sys.modules
    if name == "tkinter"
    or name.startswith("win32com")
    or "ai_editorial_service" in name
    or "structure_ai_arbitrator" in name
    or ".ui" in name
    or "word_" in name
    or ".services." in name
    or ".pipeline." in name
]
print(json.dumps(forbidden))
"""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == "[]"


def test_importing_native_etc_rule_stays_isolated() -> None:
    code = """
import json
import sys
import purh_editorial.rules.orthotypography.etc_rule
forbidden = [
    name for name in sys.modules
    if name == "tkinter"
    or name.startswith("win32com")
    or "ai_editorial_service" in name
    or "structure_ai_arbitrator" in name
    or ".ui" in name
    or "word_" in name
    or ".services." in name
    or ".pipeline." in name
]
print(json.dumps(forbidden))
"""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == "[]"


def test_shadow_adapter_adds_no_pipeline_ui_word_or_ai_imports() -> None:
    code = """
import json
import sys
import purh_editorial.services
before = set(sys.modules)
import purh_editorial.services.orthotypo_shadow_adapter
forbidden = [
    name for name in set(sys.modules) - before
    if name == "tkinter"
    or name.startswith("win32com")
    or "ai_editorial_service" in name
    or "structure_ai_arbitrator" in name
    or ".ui" in name
    or "word_" in name
    or ".pipeline." in name
]
print(json.dumps(forbidden))
"""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == "[]"


def test_existing_services_and_pipeline_do_not_import_the_new_package() -> None:
    paths = [
        ROOT / "src/purh_editorial/services/orthotypo_service.py",
        ROOT / "src/purh_editorial/services/footnote_normalizer.py",
        ROOT / "src/purh_editorial/services/bibliography_normalizer.py",
        ROOT / "src/purh_editorial/services/structure_service.py",
        ROOT / "src/purh_editorial/pipeline/step1.py",
    ]
    for path in paths:
        assert "purh_editorial.rules" not in path.read_text(encoding="utf-8")


def test_existing_services_pipeline_and_configuration_do_not_import_shadow() -> None:
    roots = [
        ROOT / "src/purh_editorial/services",
        ROOT / "src/purh_editorial/pipeline",
        ROOT / "src/purh_editorial/ui",
    ]
    for root in roots:
        for path in root.rglob("*.py"):
            if path.name == "orthotypo_shadow_adapter.py":
                continue
            assert "purh_editorial.rules.shadow" not in path.read_text(
                encoding="utf-8"
            )


def test_shadow_adapter_is_not_wired_into_production_entry_points() -> None:
    roots = [
        ROOT / "src/purh_editorial/pipeline",
        ROOT / "src/purh_editorial/ui",
        ROOT / "src/purh_editorial/config",
    ]
    paths = [
        ROOT / "src/purh_editorial/services/orthotypo_service.py",
        ROOT / "src/purh_editorial/services/__init__.py",
    ]
    paths.extend(
        path
        for root in roots
        for path in root.rglob("*.py")
    )
    for path in paths:
        content = path.read_text(encoding="utf-8")
        assert "orthotypo_shadow_adapter" not in content
        assert "EtcAbbreviationRule" not in content

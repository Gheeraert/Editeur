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


def test_importing_native_redoublement_rule_stays_isolated() -> None:
    code = """
import json
import sys
import purh_editorial.rules.orthotypography.redoublement_rule
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


def test_importing_native_ordinal_rule_stays_isolated() -> None:
    code = """
import json
import sys
import purh_editorial.rules.orthotypography.ordinal_rule
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


def test_importing_shadow_adapter_stays_isolated() -> None:
    code = """
import json
import sys
import purh_editorial.services.orthotypo_shadow_adapter
forbidden = [
    name for name in sys.modules
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


def test_importing_redoublement_shadow_adapter_stays_isolated() -> None:
    code = """
import json
import sys
import purh_editorial.services.orthotypo_redoublement_shadow_adapter
forbidden = [
    name for name in sys.modules
    if name == "tkinter"
    or name.startswith("win32com")
    or "ai_editorial_service" in name
    or "structure_ai_arbitrator" in name
    or ".ui" in name
    or "word_" in name
    or (
        name == "purh_editorial.pipeline"
        or name.startswith("purh_editorial.pipeline.")
    )
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


def test_importing_ordinal_shadow_adapter_stays_isolated() -> None:
    code = """
import json
import sys
import purh_editorial.services.orthotypo_ordinal_shadow_adapter
forbidden = [
    name for name in sys.modules
    if name == "tkinter"
    or name.startswith("win32com")
    or "ai_editorial_service" in name
    or "structure_ai_arbitrator" in name
    or ".ui" in name
    or "word_" in name
    or (
        name == "purh_editorial.pipeline"
        or name.startswith("purh_editorial.pipeline.")
    )
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


def test_importing_orthotypo_shadow_batch_stays_isolated() -> None:
    code = """
import json
import sys
import purh_editorial.services.orthotypo_shadow_batch
forbidden = [
    name for name in sys.modules
    if name == "tkinter"
    or name.startswith("win32com")
    or "ai_editorial_service" in name
    or "structure_ai_arbitrator" in name
    or ".ui" in name
    or "word_" in name
    or (
        name == "purh_editorial.pipeline"
        or name.startswith("purh_editorial.pipeline.")
    )
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


def test_importing_private_shadow_evaluation_tool_stays_isolated() -> None:
    tool_path = ROOT / "tools/evaluate_orthotypo_shadow_private.py"
    code = f"""
import importlib.util
import json
import sys
spec = importlib.util.spec_from_file_location("private_shadow_tool", {str(tool_path)!r})
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
forbidden = [
    name for name in sys.modules
    if name == "tkinter"
    or name.startswith("win32com")
    or "ai_editorial_service" in name
    or "structure_ai_arbitrator" in name
    or ".ui" in name
    or "word_review" in name
    or "word_workspace" in name
    or (
        name == "purh_editorial.pipeline"
        or name.startswith("purh_editorial.pipeline.")
    )
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


def test_importing_orthotypo_shadow_support_stays_isolated() -> None:
    code = """
import json
import sys
import purh_editorial.services.orthotypo_shadow_support
forbidden = [
    name for name in sys.modules
    if name == "tkinter"
    or name.startswith("win32com")
    or "ai_editorial_service" in name
    or "structure_ai_arbitrator" in name
    or ".ui" in name
    or "word_" in name
    or (
        name == "purh_editorial.pipeline"
        or name.startswith("purh_editorial.pipeline.")
    )
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
            if path.name in {
                "orthotypo_shadow_adapter.py",
                "orthotypo_redoublement_shadow_adapter.py",
                "orthotypo_ordinal_shadow_adapter.py",
                "orthotypo_shadow_batch.py",
                "orthotypo_shadow_support.py",
            }:
                continue
            assert "purh_editorial.rules.shadow" not in path.read_text(
                encoding="utf-8"
            )
            assert "orthotypo_shadow_support" not in path.read_text(
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
        assert "orthotypo_redoublement_shadow_adapter" not in content
        assert "orthotypo_ordinal_shadow_adapter" not in content
        assert "orthotypo_shadow_batch" not in content
        assert "orthotypo_shadow_support" not in content
        assert "EtcAbbreviationRule" not in content
        assert "RedoubledAbbreviationRule" not in content
        assert "OrdinalAbbreviationRule" not in content


def test_existing_etc_adapter_and_support_do_not_know_redoublement() -> None:
    paths = [
        ROOT / "src/purh_editorial/services/orthotypo_shadow_adapter.py",
        ROOT / "src/purh_editorial/services/orthotypo_shadow_support.py",
    ]
    for path in paths:
        content = path.read_text(encoding="utf-8")
        assert "purh.abreviations.redoublement" not in content
        assert "RedoubledAbbreviationRule" not in content


def test_existing_adapters_and_support_do_not_know_ordinal() -> None:
    paths = [
        ROOT / "src/purh_editorial/services/orthotypo_shadow_adapter.py",
        ROOT / "src/purh_editorial/services/orthotypo_redoublement_shadow_adapter.py",
        ROOT / "src/purh_editorial/services/orthotypo_shadow_support.py",
    ]
    for path in paths:
        content = path.read_text(encoding="utf-8")
        assert "purh.ordinaux" not in content
        assert "OrdinalAbbreviationRule" not in content


def test_private_evaluation_tool_is_not_wired_into_production() -> None:
    paths = [
        ROOT / "src/purh_editorial/services/__init__.py",
        *(
            path
            for root in (
                ROOT / "src/purh_editorial/pipeline",
                ROOT / "src/purh_editorial/ui",
            )
            for path in root.rglob("*.py")
        ),
    ]
    for path in paths:
        assert "evaluate_orthotypo_shadow_private" not in path.read_text(
            encoding="utf-8"
        )


def test_private_tool_is_the_only_consumer_of_shadow_batch() -> None:
    batch_import = "purh_editorial.services.orthotypo_shadow_batch"
    for path in (ROOT / "src/purh_editorial/services").glob("*.py"):
        if path.name == "orthotypo_shadow_batch.py":
            continue
        assert batch_import not in path.read_text(encoding="utf-8")
    tool_path = ROOT / "tools/evaluate_orthotypo_shadow_private.py"
    assert batch_import in tool_path.read_text(encoding="utf-8")

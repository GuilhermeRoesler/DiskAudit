#!/usr/bin/env python3
"""Smoke e testes de borda da auditoria de disco (unittest, sem deps extras)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import disk_audit as da  # noqa: E402
from scripts.validate_csv import validate  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "sample.csv"


class TestDiskAuditSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.frames = da.load_csv(FIXTURE)
        cls.data, cls.root, cls.user = da.analyze(cls.frames)

    def test_detect_root(self) -> None:
        self.assertEqual(self.root, "C:\\")

    def test_detect_user_profile(self) -> None:
        self.assertEqual(self.user, "C:\\Users\\TestUser\\")

    def test_tier_keys(self) -> None:
        self.assertEqual(set(self.data["tier_totals"]), {"seguro", "cuidado", "nao_tocar"})

    def test_tier_totals_are_floats(self) -> None:
        for key, value in self.data["tier_totals"].items():
            self.assertIsInstance(value, float, key)

    def test_browser_cache_targets_cache_dirs_only(self) -> None:
        paths = {c["path"] for c in self.data["candidates"] if c["category"] == "Cache de navegador"}
        self.assertTrue(any(p.endswith("\\cache2") for p in paths), paths)
        self.assertTrue(any("Opera Software" in p and p.endswith("\\Cache") for p in paths), paths)
        self.assertTrue(any(p.endswith("\\Cache") and "Chrome" in p for p in paths), paths)
        self.assertFalse(any(p.endswith("\\Opera Software") for p in paths), paths)
        self.assertFalse(any(p.endswith("\\Profiles") for p in paths), paths)

    def test_node_modules_rationale_uses_gb(self) -> None:
        nm = next(c for c in self.data["candidates"] if c["category"] == "Dev (node_modules)")
        self.assertIn("GB", nm["rationale"])
        self.assertNotIn(" MB)", nm["rationale"])
        self.assertRegex(nm["rationale"], r"frontend \(2\.5 GB\)")
        self.assertRegex(nm["rationale"], r"backend \(1\.8 GB\)")

    def test_safe_includes_recycle_and_temp(self) -> None:
        safe_paths = {c["path"] for c in self.data["candidates"] if c["risk"] == "seguro"}
        self.assertTrue(any("Recycle.Bin" in p for p in safe_paths))
        self.assertTrue(any(p.endswith("\\Temp") for p in safe_paths))

    def test_documents_nao_tocar_only_in_profile(self) -> None:
        docs = [c for c in self.data["candidates"] if c["category"] == "Pessoal (documentos)"]
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["risk"], "nao_tocar")
        self.assertTrue(docs[0]["path"].startswith("C:\\Users\\TestUser\\"))

    def test_demo_recovery_story_numbers(self) -> None:
        """Números estáveis do fixture — usados no README de portfólio."""
        self.assertEqual(self.data["root_gb"], 250.0)
        self.assertAlmostEqual(self.data["tier_totals"]["seguro"], 18.1, places=1)
        self.assertAlmostEqual(self.data["tier_totals"]["cuidado"], 27.0, places=1)
        self.assertAlmostEqual(self.data["tier_totals"]["nao_tocar"], 35.5, places=1)


class TestEdgeCases(unittest.TestCase):
    def test_missing_csv_returns_error(self) -> None:
        code = da.main(["__missing_disk_audit__.csv"])
        self.assertEqual(code, 1)

    def test_invalid_csv_fails_validator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.csv"
            bad.write_text("Name,Size\nfoo,1\n", encoding="utf-8")
            errors, _warnings = validate(bad)
            self.assertTrue(errors)

    def test_empty_csv_fails_validator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty.csv"
            empty.write_text("", encoding="utf-8")
            errors, _warnings = validate(empty)
            self.assertTrue(errors)

    def test_root_fallback_without_drive_letter_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "noroot.csv"
            csv_path.write_text(
                "\n".join(
                    [
                        "Nome,Arquivos,Subdiretórios,Tamanho Físico,Tamanho Lógico,Última Alteração",
                        "D:\\Data,10,2,5000000000,5000000000,2024-01-01T00:00:00",
                        "D:\\Data\\logs,5,0,1000000000,1000000000,2024-01-01T00:00:00",
                        "D:\\Data\\cache.tmp,0,0,500000000,500000000,2024-01-01T00:00:00",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            frames = da.load_csv(csv_path)
            data, root, user = da.analyze(frames)
            self.assertTrue(root.endswith("\\"))
            self.assertIsNone(user)
            self.assertEqual(set(data["tier_totals"]), {"seguro", "cuidado", "nao_tocar"})
            self.assertEqual(sum(data["tier_totals"].values()), 0.0)

    def test_render_html_writes_file(self) -> None:
        frames = da.load_csv(FIXTURE)
        data, root, user = da.analyze(frames)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report.html"
            template_dir = ROOT / "diskaudit" / "templates"
            da.render_html(data, root, user, template_dir, out)
            html = out.read_text(encoding="utf-8")
            self.assertIn("const DATA", html)
            self.assertIn("TestUser", html)


class TestValidateFixture(unittest.TestCase):
    def test_sample_fixture_is_valid(self) -> None:
        errors, warnings = validate(FIXTURE)
        self.assertEqual(errors, [])
        self.assertTrue(any("Raiz detectada" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()

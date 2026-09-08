#!/usr/bin/env python3
"""Smoke tests da auditoria de disco (unittest, sem deps extras)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import disk_audit as da  # noqa: E402

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

    def test_browser_cache_targets_cache_dirs_only(self) -> None:
        paths = {c["path"] for c in self.data["candidates"] if c["category"] == "Cache de navegador"}
        self.assertTrue(any(p.endswith("\\cache2") for p in paths), paths)
        self.assertTrue(any("Opera Software" in p and p.endswith("\\Cache") for p in paths), paths)
        self.assertTrue(any(p.endswith("\\Cache") and "Chrome" in p for p in paths), paths)
        # Pastas de produto/perfil NÃO devem ser "seguro" como cache
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


if __name__ == "__main__":
    unittest.main()

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
from diskaudit import __version__  # noqa: E402
from diskaudit.cli import main as cli_main  # noqa: E402
from diskaudit.render import build_executive_summary  # noqa: E402
from diskaudit.validate import validate  # noqa: E402

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
        self.assertAlmostEqual(self.data["tier_totals"]["seguro"], 21.7, places=1)
        self.assertAlmostEqual(self.data["tier_totals"]["cuidado"], 44.4, places=1)
        self.assertAlmostEqual(self.data["tier_totals"]["nao_tocar"], 43.0, places=1)

    def test_ollama_targets_updates_v2_only(self) -> None:
        updater = next(c for c in self.data["candidates"] if c["category"] == "Cache de updater")
        self.assertTrue(updater["path"].endswith("\\updates_v2"))
        self.assertEqual(updater["risk"], "seguro")
        self.assertFalse(
            any(
                c["path"].endswith("\\Ollama") and c["category"] == "Cache de updater"
                for c in self.data["candidates"]
            )
        )

    def test_dist_detected_via_csv_markers(self) -> None:
        dist = [c for c in self.data["candidates"] if c["category"] == "Dev (build artifact)"]
        self.assertEqual(len(dist), 1)
        self.assertTrue(dist[0]["path"].endswith("\\dist"))
        self.assertEqual(dist[0]["risk"], "seguro")

    def test_expanded_rationales_present(self) -> None:
        by_path_suffix = {c["path"].rstrip("\\").split("\\")[-1]: c for c in self.data["candidates"]}

        wsl = next(c for c in self.data["candidates"] if c["category"] == "Dev (WSL)")
        self.assertIn("distro(s) WSL", wsl["rationale"])

        llm = next(c for c in self.data["candidates"] if c["category"] == "Modelos LLM")
        self.assertIn("llama-7b", llm["rationale"])

        android = [c for c in self.data["candidates"] if c["category"] == "Dev (Android)"]
        self.assertGreaterEqual(len(android), 2)
        self.assertTrue(any("SDK" in c["rationale"] for c in android))
        self.assertTrue(any("Emuladores" in c["rationale"] for c in android))

        minecraft = next(
            c for c in self.data["candidates"] if c["category"] == "Jogo" and "minecraft" in c["path"].lower()
        )
        self.assertIn("mods", minecraft["rationale"].lower())

        docker = next(c for c in self.data["candidates"] if c["category"] == "Dev (Docker)")
        self.assertIn("docker_data.vhdx", docker["rationale"])

        orphan = next(c for c in self.data["candidates"] if c["category"] == "App órfão")
        self.assertIn("UWP", orphan["rationale"])

        downloads = [c for c in self.data["candidates"] if c["category"] == "Downloads"]
        self.assertTrue(downloads)
        self.assertIn(".zip", downloads[0]["rationale"])

        npm = next(c for c in self.data["candidates"] if c["path"].endswith("\\npm-cache"))
        self.assertIn("pnpm", npm["rationale"])
        self.assertIn("pip", npm["rationale"])

        updater = next(c for c in self.data["candidates"] if c["category"] == "Cache de updater")
        self.assertIn("OllamaSetup.exe", updater["rationale"])

        pagefile = next(c for c in self.data["candidates"] if c["path"].endswith("pagefile.sys"))
        self.assertEqual(pagefile["risk"], "nao_tocar")
        self.assertIn("sistema", pagefile["rationale"].lower())
        self.assertIn("pagefile.sys", by_path_suffix)

    def test_executive_summary_mentions_recovery(self) -> None:
        html = build_executive_summary(self.data, self.user)
        self.assertIn("recuperáveis com segurança", html)
        self.assertIn("TestUser", html)


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
            self.assertIn('name="viewport"', html)
            self.assertIn("og:title", html)
            self.assertIn(f"disk-audit</a> v{__version__}", html)
            self.assertIn("Chart", html)


class TestCli(unittest.TestCase):
    def test_cli_generates_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.html"
            code = cli_main([str(FIXTURE), "-o", str(out)])
            self.assertEqual(code, 0)
            self.assertTrue(out.is_file())
            self.assertIn("Auditoria de disco", out.read_text(encoding="utf-8"))

    def test_cli_custom_template_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "custom.html"
            code = cli_main(
                [
                    str(FIXTURE),
                    "-o",
                    str(out),
                    "-t",
                    str(ROOT / "diskaudit" / "templates"),
                ]
            )
            self.assertEqual(code, 0)
            self.assertTrue(out.is_file())

    def test_cli_missing_file(self) -> None:
        self.assertEqual(cli_main([str(ROOT / "no_such_file.csv")]), 1)

    def test_cli_rejects_invalid_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.csv"
            bad.write_text("Name,Size\nfoo,1\n", encoding="utf-8")
            out = Path(tmp) / "out.html"
            self.assertEqual(cli_main([str(bad), "-o", str(out)]), 1)
            self.assertFalse(out.exists())

    def test_cli_no_validate_skips_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # CSV válido estruturalmente, mas exercita a flag
            out = Path(tmp) / "out.html"
            code = cli_main([str(FIXTURE), "-o", str(out), "--no-validate"])
            self.assertEqual(code, 0)
            self.assertTrue(out.is_file())


class TestExecutiveSummaryEscape(unittest.TestCase):
    def test_summary_escapes_html_in_paths(self) -> None:
        data = {
            "root_gb": 10.0,
            "root_files": 1,
            "tier_totals": {"seguro": 1.0, "cuidado": 2.0, "nao_tocar": 0.0},
            "level2": [{"path": "C:\\Users", "gb": 5.0, "files": 1}],
            "appdata_local": [],
            "appdata_roaming": [],
            "top_files": [],
            "pattern_summary": [],
            "candidates": [
                {
                    "path": "C:\\Users\\x\\<script>evil</script>",
                    "size": 1.5,
                    "risk": "seguro",
                    "category": "Cache",
                    "action": "Limpar",
                    "rationale": "x",
                }
            ],
            "years_data": [],
            "ext_top": [],
            "compression_delta_gb": 0.0,
            "row_count": 1,
        }
        html = build_executive_summary(data, "C:\\Users\\<evil>\\")  # type: ignore[arg-type]
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&lt;evil&gt;", html)


class TestValidateFixture(unittest.TestCase):
    def test_sample_fixture_is_valid(self) -> None:
        errors, warnings = validate(FIXTURE)
        self.assertEqual(errors, [])
        self.assertTrue(any("Raiz detectada" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()

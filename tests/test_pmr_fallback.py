"""Owner-resolution regression in copied vanilla plantation investment priorities."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import generate


class PmrFallbackTests(unittest.TestCase):
    @unittest.skipUnless((generate.GAME / "common/buildings/04_plantations.txt").exists(),
                         "The installed vanilla building definitions are required")
    def test_plantation_formulas_preserved_except_explicit_owner_guards(self):
        source = (generate.GAME / "common/buildings/04_plantations.txt").read_text(encoding="utf-8-sig")
        cases = {
            "cotton_plantation": "fabric", "dye_plantation": "dye", "opium_plantation": "opium",
            "tea_plantation": "tea", "tobacco_plantation": "tobacco",
        }
        for name, good in cases.items():
            with self.subTest(building=name):
                inject, fallback = generate.building_inject(source, name, good)
                begin = source.index(f"building_{name} = {{")
                building = source[begin:generate.block_end(source, source.index("{", begin))]
                ai = re.search(r"\n\tai_value = (\{)", building)
                vanilla = re.sub(r"(?m)^\t", "", building[ai.start(1):generate.block_end(building, ai.start(1))]).rstrip() + "\n}"
                guarded = fallback.removeprefix(f"pmr_ai_value_{name} = ").rstrip()
                # Require a real owner and optional dereference. Reversing only this
                # safety change must recover the original vanilla formula byte-for-byte.
                guard = r"(?m)^([ \t]*)exists = owner\n\1owner([ \t]*)\?=([ \t]*)(?=\{)"
                self.assertEqual(len(re.findall(guard, guarded)), 1)
                self.assertEqual(re.sub(guard, r"\1owner\2=\3", guarded), vanilla)
                self.assertNotRegex(guarded, r"(?m)^[ \t]*owner[ \t]*=[ \t]*\{")
                self.assertIn(f"value = pmr_ai_value_{name}", inject)

    def test_owner_free_scalar_and_default_priorities_remain_unchanged(self):
        for source, expected in [
            ("building_probe = {\n\tai_value = 750 # explicit vanilla priority\n}\n", 750),
            ("building_probe = {\n\tbuilding_group = bg_plantations\n}\n", 1000),
        ]:
            with self.subTest(expected=expected):
                _, fallback = generate.building_inject(source, "probe", "grain")
                self.assertEqual(fallback, f"pmr_ai_value_probe = {{\n\tvalue = {expected}\n}}\n")


if __name__ == "__main__":
    unittest.main()

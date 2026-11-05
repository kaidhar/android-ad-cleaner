"""vivo V27: a row wraps its real switch in an outer Switch that always reports checked=false."""
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tool"))
sys.path.insert(0, str(ROOT / "tests"))
from fixtures import phone_stub


def row(title, sub, y, inner_on, outer_on="false"):
    return (f'<node class="android.widget.Switch" text="" content-desc="{title}.{sub}" checkable="true" checked="{outer_on}" '
            f'clickable="true" enabled="true" package="com.vivo.appstore" bounds="[0,{y}][1080,{y + 240}]">'
            f'<node class="android.widget.TextView" text="{title}" checkable="false" checked="false" clickable="false" enabled="true" bounds="[66,{y + 40}][600,{y + 100}]"/>'
            f'<node class="android.widget.TextView" text="{sub}" checkable="false" checked="false" clickable="false" enabled="true" bounds="[66,{y + 100}][700,{y + 200}]"/>'
            f'<node class="android.widget.Switch" text="" content-desc="" checkable="true" checked="{inner_on}" clickable="false" enabled="true" bounds="[888,{y + 72}][1020,{y + 172}]"/>'
            f'</node>')


class NestedSwitch(unittest.TestCase):
    def phone(self, xml):
        p = phone_stub("test", d=Mock())
        p.W, p.H = 1080, 2400
        p.d.window_size.return_value = (p.W, p.H)
        p.tree = Mock(return_value=ET.fromstring(xml))
        return p

    def states(self, xml):
        return {t: c for t, c, _ in self.phone(xml).switches()}

    def test_inner_on_means_on(self):
        xml = f'<hierarchy>{row("Notifications", "Receive timely notifications", 400, "true")}</hierarchy>'
        self.assertIs(self.states(xml)["Notifications"], True)

    def test_inner_off_means_off(self):
        xml = f'<hierarchy>{row("Notifications", "Receive timely notifications", 400, "false")}</hierarchy>'
        self.assertIs(self.states(xml)["Notifications"], False)

    def test_each_row_is_read_for_itself(self):
        xml = ("<hierarchy>" + row("Update reminders", "Show reminders", 200, "true")
               + row("Notifications", "Receive timely", 500, "false") + row("App auto-update", "Over Wi-Fi", 800, "true") + "</hierarchy>")
        self.assertEqual(self.states(xml), {"Update reminders": True, "Notifications": False, "App auto-update": True})

    def test_a_card_that_reports_on_is_still_on(self):
        xml = f'<hierarchy>{row("Notifications", "Receive timely", 400, "false", outer_on="true")}</hierarchy>'
        self.assertIs(self.states(xml)["Notifications"], True)


class Recipe(unittest.TestCase):
    def load(self, phone):
        path = ROOT / "recipes/vivo-V2231/recipe.py"
        scope = {"p": phone, "ONLY": ["__no_steps__"]}
        exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), scope)
        return scope

    def test_leaves_the_apps_selected_page_by_homepage(self):
        p = Mock()
        p.tab.side_effect = [False, True]
        p.tap.return_value = True
        self.assertTrue(self.load(p)["store_manage_tab"]())
        p.tap.assert_called_once_with("Homepage", exact=True, scrolls=0, quiet=True)
        p.back.assert_not_called()

    def test_never_taps_get(self):
        src = (ROOT / "recipes/vivo-V2231/recipe.py").read_text(encoding="utf-8")
        self.assertNotIn('tap("Get', src)
        self.assertNotIn('entry("Get', src)

    def test_gives_up_rather_than_guessing(self):
        p = Mock()
        p.tab.return_value = False
        p.tap.return_value = False
        self.assertFalse(self.load(p)["store_manage_tab"]())
        self.assertEqual(p.back.call_count, 3)

    def test_only_touches_what_it_names(self):
        src = (ROOT / "recipes/vivo-V2231/recipe.py").read_text(encoding="utf-8")
        self.assertIn('BUILD = "PD2269F_EX_A_15"', src)
        self.assertIn('MODELS = ["V2231"]', src)
        self.assertEqual(src.count("p.off("), 2)
        self.assertEqual(src.count("only="), 2)

    def test_matched_for_this_phone(self):
        import run
        path, ref = run.recipe_for("V2231", "vivo")
        self.assertFalse(ref)
        self.assertIn("vivo-V2231", path)


if __name__ == "__main__":
    unittest.main()

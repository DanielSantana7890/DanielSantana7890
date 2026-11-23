"""Regression checks for animated images in the GitHub profile README.

Run with: python -I -m unittest discover -s tests
"""

from html.parser import HTMLParser
from pathlib import Path
import unittest
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SVG = {"svg": "http://www.w3.org/2000/svg"}
ANIMATED = {
    "terminal.svg", "editor.svg", "intro.svg", "rodape.svg",
    "h-sobre.svg", "h-skills.svg", "h-estatisticas.svg",
    "h-objetivos.svg", "h-contribuicoes.svg",
}


class Images(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []
        self.sources = []
        self.links = []
        self.stack = []

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag == "a":
            self.stack.append(attributes.get("href"))
        elif tag == "img":
            self.images.append((attributes, self.stack[-1] if self.stack else None))
        elif tag == "source":
            self.sources.append(attributes)

    def handle_endtag(self, tag):
        if tag == "a" and self.stack:
            self.stack.pop()


class ProfileAnimations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.readme = (ROOT / "README.md").read_text(encoding="utf-8")
        cls.parser = Images()
        cls.parser.feed(cls.readme)

    def test_no_automatic_static_substitution(self):
        # SVGs loaded through picture sources were silently replaced when the
        # browser reported reduced motion, so no animation ever reached it.
        self.assertFalse(any("assets/static/" in source.get("srcset", "")
                             for source in self.parser.sources))
        self.assertNotIn("prefers-reduced-motion", self.readme)

    def test_all_animated_images_are_linked_and_versioned(self):
        found = set()
        for attributes, link in self.parser.images:
            url = urlsplit(attributes.get("src", ""))
            if not url.path.startswith("assets/"):
                continue
            self.assertTrue((ROOT / url.path).is_file(), url.path)
            name = Path(url.path).name
            if name in ANIMATED:
                found.add(name)
                self.assertEqual(url.query, "v=animated-2")
                self.assertTrue(link and link.endswith("/assets/" + name), name)
        self.assertEqual(found, ANIMATED)

    def test_svg_animations_exist_and_repeat(self):
        for name in ANIMATED:
            with self.subTest(svg=name):
                content = (ROOT / "assets" / name).read_text(encoding="utf-8")
                document = ET.fromstring(content)
                self.assertNotIn("prefers-reduced-motion", content)
                if name == "intro.svg":
                    animations = document.findall(".//svg:animate", SVG)
                    self.assertTrue(animations)
                    self.assertTrue(all(node.get("repeatCount") == "indefinite"
                                        for node in animations))
                else:
                    self.assertIn("@keyframes", content)
                    self.assertIn("infinite", content)
                    self.assertNotIn("forwards", content)
                self.assertFalse(document.findall(".//svg:script", SVG))

    def test_original_profile_elements_preserved(self):
        self.assertIn("Welcome+to+my+profile!", self.readme)
        self.assertIn("Instagram-E4405F", self.readme)
        self.assertIn("LinkedIn-0077B5", self.readme)
        self.assertIn("width=\"46%\" align=\"right\"", self.readme)
        self.assertIn("github-contribution-grid-snake-dark.svg", self.readme)
        self.assertNotIn("komarev.com", self.readme)
        self.assertNotIn("<samp>", self.readme)


if __name__ == "__main__":
    unittest.main()

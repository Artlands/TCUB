import unittest

from taskbound_core import path_matches


class TestGlob(unittest.TestCase):
    def test_star_stays_within_one_segment(self):
        self.assertTrue(path_matches("/projects/A/file.txt", "/projects/A/*"))
        # '*' must not cross '/', so it does not reach a nested path
        self.assertFalse(path_matches("/projects/A/sub/file.txt", "/projects/A/*"))

    def test_doublestar_crosses_separators(self):
        self.assertTrue(path_matches("/projects/A/sub/deep/file", "/projects/A/**"))
        self.assertTrue(path_matches("/projects/A/file", "/projects/A/**"))
        self.assertFalse(path_matches("/projects/B/file", "/projects/A/**"))

    def test_question_mark_single_char(self):
        self.assertTrue(path_matches("/a/b1", "/a/b?"))
        self.assertFalse(path_matches("/a/b12", "/a/b?"))
        self.assertFalse(path_matches("/a/b/1", "/a/b?"))

    def test_anchored_whole_string(self):
        self.assertFalse(path_matches("/projects/A/file/extra", "/projects/A/file"))
        self.assertTrue(path_matches("/projects/A/file", "/projects/A/file"))

    def test_literal_regex_chars_are_escaped(self):
        self.assertTrue(path_matches("/a.b/c+d", "/a.b/c+d"))
        self.assertFalse(path_matches("/axb/c+d", "/a.b/c+d"))


if __name__ == "__main__":
    unittest.main()

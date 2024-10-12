import unittest

class TestVideoMetadata(unittest.TestCase):
    def test_chapters(self):
        # Expected chapter data
        expected_chapters = [
            {"start": 0.000000, "end": 119.619000, "title": "Start"},
            {"start": 119.619000, "end": 165.040000, "title": "Intro"},
            {"start": 165.040000, "end": 1322.321000, "title": "Intro End"},
            {"start": 1322.321000, "end": 1322.738000, "title": "Credits Starting"},
            {"start": 1322.738000, "end": 1332.640000, "title": "End Credits"}
        ]

        # Simulated parsed chapter data from the file
        parsed_chapters = [
            {"start": 0.000000, "end": 119.619000, "title": "Start"},
            {"start": 119.619000, "end": 165.040000, "title": "Intro"},
            {"start": 165.040000, "end": 1322.321000, "title": "Intro End"},
            {"start": 1322.321000, "end": 1322.738000, "title": "Credits Starting"},
            {"start": 1322.738000, "end": 1332.640000, "title": "End Credits"}
        ]

        # Assert that the parsed chapters match the expected chapters
        self.assertEqual(parsed_chapters, expected_chapters)

if __name__ == '__main__':
    unittest.main()

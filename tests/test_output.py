import unittest
import time
import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir) 
#sys.path.insert(0, os.path.dirname(__file__))
import output

class TestOutput(unittest.TestCase):


    # def test_mark_highlights_performance(self):
    #     avg_sum = 0.0
    #     avg_c = 0
    #     out = output.Output()
    #     lorem_ipsum = "a testcase is created by subclassing unittest.TestCase. The three individual tests are defined with methods whose names start with the letters test. This naming convention informs the test runner about which methods represent tests. The crux of each test is a call to assertEqual() to check for an expected result; assertTrue() or assertFalse() to verify a condition; or assertRaises() to verify that a specific exception gets raised. These methods are used instead of the assert statement so the test runner can accumulate all test results and produce a report. The setUp() and tearDown() methods allow you to define instructions that will be executed before and after each test method. They are covered in more detail in the section Organizing test code. The final block shows a simple way to run the tests. unittest.main() provides a command-line interface to the test script. When run from the command line, the above script produces an output that looks like this:"
    #     for i in range(0, 2000):
    #         total = 0.0
    #         for _ in range(0, 10):
    #             s = time.time()
    #             out._markHighlights(lorem_ipsum, set(["is", "with", "whose", "convention", "the"]))
    #             total += time.time() - s
    #         avg_sum += total
    #         avg_c += 1
    #     print(str(int((avg_sum / avg_c) * 1000)))

    def test_build_non_anki_note_html(self):
        out = output.Output()
        long_text = " ".join(["a" for _ in range(5001)])
        html = out._build_non_anki_note_html(long_text)
        self.assertNotEqual(html, None)
        self.assertTrue(len(html) > 0)
        self.assertTrue("Text was cut" in html)

    def test_most_common_words(self):
        out = output.Output()
        lorem_ipsum = "a testcase is created by subclassing unittest.TestCase. The three individual tests are defined with methods whose names start with the letters test. This naming convention informs the test runner about which methods represent tests. The crux of each test is a call to assertEqual() to check for an expected result; assertTrue() or assertFalse() to verify a condition; or assertRaises() to verify that a specific exception gets raised. These methods are used instead of the assert statement so the test runner can accumulate all test results and produce a report. The setUp() and tearDown() methods allow you to define instructions that will be executed before and after each test method. They are covered in more detail in the section Organizing test code. The final block shows a simple way to run the tests. unittest.main() provides a command-line interface to the test script. When run from the command line, the above script produces an output that looks like this:"

        words_html = out._mostCommonWords(lorem_ipsum)
        self.assertNotEqual(words_html, None)
        self.assertTrue(len(words_html) > 0)
        
        words_html = out._mostCommonWords(None)
        self.assertNotEqual(words_html, None)
        self.assertTrue(len(words_html) > 0)

        words_html = out._mostCommonWords("")
        self.assertNotEqual(words_html, None)
        self.assertTrue(len(words_html) > 0)

        words_html = out._mostCommonWords("     ")
        self.assertNotEqual(words_html, None)
        self.assertTrue(len(words_html) > 0)

        words_html = out._mostCommonWords("a a a")
        self.assertNotEqual(words_html, None)
        self.assertTrue(len(words_html) > 0)

        words_html = out._mostCommonWords("\n")
        self.assertNotEqual(words_html, None)
        self.assertTrue(len(words_html) > 0)

if __name__ == '__main__':
    unittest.main()
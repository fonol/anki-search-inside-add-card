import unittest
import time
import random
import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir).replace("\\", "/")+ "/src/"
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, parentdir) 
sys.path.insert(0, "D:/anki-master/") 

from output import Output

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
    #             out._mark_highlights(lorem_ipsum, set(["is", "with", "whose", "convention", "the"]))
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
        out = Output()
        lorem_ipsum = "a testcase is created by subclassing unittest.TestCase. The three individual tests are defined with methods whose names start with the letters test. This naming convention informs the test runner about which methods represent tests. The crux of each test is a call to assertEqual() to check for an expected result; assertTrue() or assertFalse() to verify a condition; or assertRaises() to verify that a specific exception gets raised. These methods are used instead of the assert statement so the test runner can accumulate all test results and produce a report. The setUp() and tearDown() methods allow you to define instructions that will be executed before and after each test method. They are covered in more detail in the section Organizing test code. The final block shows a simple way to run the tests. unittest.main() provides a command-line interface to the test script. When run from the command line, the above script produces an output that looks like this:"

        words_html = out._most_common_words(lorem_ipsum)
        self.assertNotEqual(words_html, None)
        self.assertTrue(len(words_html) > 0)
        
        words_html = out._most_common_words(None)
        self.assertNotEqual(words_html, None)
        self.assertTrue(len(words_html) > 0)

        words_html = out._most_common_words("")
        self.assertNotEqual(words_html, None)
        self.assertTrue(len(words_html) > 0)

        words_html = out._most_common_words("     ")
        self.assertNotEqual(words_html, None)
        self.assertTrue(len(words_html) > 0)

        words_html = out._most_common_words("a a a")
        self.assertNotEqual(words_html, None)
        self.assertTrue(len(words_html) > 0)

        words_html = out._most_common_words("\n")
        self.assertNotEqual(words_html, None)
        self.assertTrue(len(words_html) > 0)

        s = time.time() * 1000
        words_html = out._most_common_words(lorem_ipsum * 5)
        e = time.time() * 1000 - s
        self.assertTrue(e < 50)


    
    def test_print_search_results_perf(self):
        out = self.get_output()
        db_list = []
        text = self.get_lorem_ipsum_note_text()
        for i in range(1, 1000):
            tags = self.get_tags(i)
            db_list.append((text, tags, 1, i, 0, 1, ""))

        query_set = set(["three", "tests", "whose", "methods", "instead", "way", "output", "this", "script"])
        t_sum = 0.0
        highlight_sum = 0.0
        user_note_sum = 0.0

        reps = 5000
        for i in range(0, reps):
            s = time.time() * 1000
            r = out.print_search_results(db_list, None, None, False, False, 1, query_set, False, False)
            t_sum += time.time() * 1000 - s
            highlight_sum += r[0]
        avg = t_sum / reps
        h_avg = highlight_sum / reps
        print(str(avg))
        print("highlighting avg ms: " + str(h_avg))
        self.assertTrue(avg < 100)



         
    def get_output(self):
        out = Output()
        out.stopwords = []
        out.remove_divs = False
        out.gridView = True
        out.scale = 1.0
        out.fields_to_hide_in_results = dict()
        out.edited = []
        out.lastResDict = {}
        out.hideSidebar = False
        return out


    def get_tags(self, i):
        n = i % 5
        tags = []
        for i in range(0, n):
            tags.append(str(i))
            if len(tags) > 0 and i % 3 == 0:
                tags.append(tags[random.randint(0, len(tags) - 1)] + "::" + str(i))
        return " ".join(tags)


    def get_lorem_ipsum_note_text(self):
        return """
            a testcase is created by subclassing unittest.TestCase. The three individual tests are defined with methods whose names start with the letters test. 
            This naming convention informs the test runner about which methods represent tests. The crux of each test is a call to assertEqual() to check for an expected result; assertTrue() 
            r assertFalse() to verify a condition; or assertRaises() to verify that a specific exception gets raised. These methods are used instead of the assert statement so 
            
        """

if __name__ == '__main__':
    unittest.main()
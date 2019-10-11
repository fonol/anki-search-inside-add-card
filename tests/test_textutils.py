import unittest
import time
import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 
#sys.path.insert(0, os.path.dirname(__file__))
import textutils

class TestTextUtils(unittest.TestCase):

    # def test_is_chinese_char_performance(self):
    #     avg_sum = 0.0
    #     avg_c = 0
        
    #     for i in range(0, 100):
    #         total = 0.0
    #         for _ in range(0, 1000):
    #             s = time.time()
    #             textutils.isChineseChar('1')
    #             textutils.isChineseChar('a')
    #             textutils.isChineseChar('也')
    #             textutils.isChineseChar('见')
    #             textutils.isChineseChar('.')
    #             textutils.isChineseChar(',')
    #             total += time.time() - s
    #         avg_sum += total
    #         avg_c += 1
    #     print(str(int((avg_sum / avg_c) * 1000)))

        

if __name__ == '__main__':
    unittest.main()
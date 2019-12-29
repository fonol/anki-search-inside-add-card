import unittest
import time
import os,sys,inspect
import random
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir).replace("\\", "/")+ "/src/"
sys.path.insert(0, parentdir ) 
import utility.tags

class TestUtilityTags(unittest.TestCase):

    def test_build_tag_map_empty_inp(self):
        tags = []
        m = utility.tags.to_tag_hierarchy(tags)
        self.assertTrue(len(m) == 0)         

    def test_build_tag_map_correct_hierarchy(self):
        tags = ["top", "top::sub"]
        m = utility.tags.to_tag_hierarchy(tags)
        self.assertTrue(len(m) == 1)
        self.assertTrue(len(m["top"]) == 1)
    
    def test_build_tag_map_large_inp(self):
        tags = []
        for i in range(1, 10000):
            tags.append(str(i))
        m = utility.tags.to_tag_hierarchy(tags)
        self.assertTrue(len(m) == len(tags))
    
    def test_build_tag_map_perf(self):
        tags = []
        for i in range(1, 30000):
            if i > 1 and random.randint(0, 2) == 0:            
                tags.append(tags[random.randint(0, len(tags)-1)] + "::" + tags[random.randint(0, len(tags) - 1)])
            tags.append(str(i))
        self.assertTrue(len(tags) > 30000)
        s = time.time() * 1000    
        m = utility.tags.to_tag_hierarchy(tags)
        e = time.time() * 1000 - s
        self.assertTrue(len(m)> 0)
        self.assertTrue(e < 500)
        

    



if __name__ == '__main__':
    unittest.main()
import os
import sys


def log(text):
    dir = os.path.dirname(os.path.realpath(__file__)).replace("\\", "/").replace("/logging.py", "")
    try:
        with open(dir + '/log.txt', 'a') as out:
            out.write(text + '\n')
    except:
        pass
import re

cleanWordReg = re.compile(r"[^\'a-zA-ZÀ-ÖØ-öø-ÿ]*(\S+?)[^\'a-zA-ZÀ-ÖØ-öø-ÿ]*")    
ignoreReg = re.compile("^[^\'a-zA-ZÀ-ÖØ-öø-ÿ]+$")    
tagReg = re.compile(r'<[^>]+>|&nbsp;', flags = re.I)
spaceReg = re.compile('\s{2,}')


def clean(text, stopWords):
    filtered = ""
    text = text.replace("\r\n", " ").replace("\n", " ")
    text = text.replace("\t", " ")
    text = text.replace("\u001f", " ")
    text = tagReg.sub(" ", text)
    text = spaceReg.sub(" ", text)
    for token in text.split(" "):
        if ignoreReg.match(token) is not None:
            continue
        if token.lower() in stopWords:
            continue
        filtered += cleanWordReg.sub(r'\1', token.strip()) + " "
    if len(filtered) > 0:
        return filtered[:-1]
    return ""


def trimIfLongerThan(text, n):
    if len(text) <= n:
        return text
    return text[:n] + "..."
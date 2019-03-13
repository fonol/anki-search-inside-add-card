import re

cleanWordReg = re.compile(r"[^\'a-zA-ZÀ-ÖØ-öø-ÿ]*(\S+?)[^\'a-zA-ZÀ-ÖØ-öø-ÿ]*")    
ignoreReg = re.compile("^[^\'a-zA-ZÀ-ÖØ-öø-ÿǒ]+$")    
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


def replaceVowelsWithAccentedRegex(text):
    text = text.replace("a", "[aàáâãåāă]")
    text = text.replace("u", "[uùúûūǔ]")
    text = text.replace("o", "[oòóôōǒ]")
    text = text.replace("e", "[eèéêëēěę]")
    text = text.replace("i", "[iìíîïīǐ]")
    text = text.replace("y", "[yýỳÿȳ]")

    text = text.replace("A", "[AÀÁÂÃÅĀĂ]")
    text = text.replace("U", "[UÙÚÛŪǓ]")
    text = text.replace("O", "[OÒÓÔŌǑ]")
    text = text.replace("E", "[EÈÉÊËĒĚĘ]")
    text = text.replace("I", "[IÌÍÎÏĪǏ]")
    text = text.replace("Y", "[YÝỲŸȲ]")

    return text

 
def deleteChars(text, chars):
    for c in chars:
        text = text.replace(c, "")
    return text


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
    stopWords = [s.lower() for s in stopWords]
    for token in text.split(" "):
        if ignoreReg.match(token) is not None:
            continue
        cleaned = cleanWordReg.sub(r'\1', token.strip())
        if len(cleaned) <= 1 or cleaned.lower() in stopWords:
            continue
        filtered += cleaned + " "
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

def replaceAccentsWithVowels(text):
    text = re.sub(r"[àáâãåāă]", "a", text)
    text = re.sub(r"[ùúûūǔ]", "u", text)
    text = re.sub(r"[òóôōǒ]", "o", text)
    text = re.sub(r"[èéêëēěę]", "e", text)
    text = re.sub(r"[ìíîïīǐ]", "i", text)
    text = re.sub(r"[ýỳÿȳ]", "y", text)
    text = re.sub(r"[ÀÁÂÃÅĀĂ]", "A", text)
    text = re.sub(r"[ÙÚÛŪǓ]", "U", text)
    text = re.sub(r"[ÒÓÔŌǑ]", "O", text)
    text = re.sub(r"[ÈÉÊËĒĚĘ]", "E", text)
    text = re.sub(r"[ÌÍÎÏĪǏ]", "I", text)
    text = re.sub(r"[ÝỲŸȲ]", "Y", text)
    return text
 
def deleteChars(text, chars):
    for c in chars:
        text = text.replace(c, "")
    return text


import re
from datetime import datetime
import time
import random

cleanWordReg = re.compile(u"^[^a-zA-ZÀ-ÖØ-öø-ÿāōūēīȳǒǎǐě\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]*(\S+?)[^a-zA-ZÀ-ÖØ-öø-ÿāōūēīȳǒǎǐě\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]*$", re.U)    
ignoreReg = re.compile(u"^[^a-zA-ZÀ-ÖØ-öø-ÿǒāōūēīȳǒǎǐě\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]+$", re.U)
nonWordReg = re.compile(u"[^a-zA-ZÀ-ÖØ-öø-ÿāōūēīȳǒǎǐě\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]", re.U) 
tagReg = re.compile(r'<[^>]+>|&nbsp;', flags = re.I)
spaceReg = re.compile('\s{2,}')
normalChar = re.compile(u"[a-zöäü\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]", re.I | re.U) 
chineseChar = re.compile(u"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]", re.U)
japaneseChar = re.compile("")

def clean(text, stopWords):
   
    filtered = ""
    text = text.replace("\r\n", " ").replace("\n", " ")
    text = text.replace("\t", " ")
    text = text.replace("\u001f", " ")
    text = tagReg.sub(" ", text)
    text = nonWordReg.sub(" ", text)
    text = spaceReg.sub(" ", text)
    stopWords = [s.lower() for s in stopWords]
    for token in tokenize(text):
        if ignoreReg.match(token) is not None:
            continue
        cleaned = cleanWordReg.sub(r'\1', token.strip())
        if (len(cleaned) <= 1 and not chineseChar.search(cleaned)) or cleaned.lower() in stopWords:
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
    text = text.replace("a", "[aàáâãåāăǎ]")
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
    text = re.sub(r"[àáâãåāăǎ]", "a", text)
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


def tokenize(text):
    result = []
    spl = text.split(" ")
    for token in spl:
        if re.search(u'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]', token):
            for char in token:
                result.append(str(char))
        else:
            result.append(token)
    return result

def textTooSmall(text):
    if len(text) > 1:
        return False
    if len(text) == 0:
        return True
    if chineseChar.search(text):
        return False
    return True

def isChineseChar(char):
    return chineseChar.search(char)


def asciiFoldChar(char):
    if normalChar.match(char):
        return char
    if char.lower() in "àáâãåāăǎ":
        return 'a'
    if char.lower() in "ùúûūǔ":
        return 'u'
    if char.lower() in "òóôōǒ":
        return 'o'
    if char.lower() in "èéêëēěę":
        return 'e'
    if char.lower() in "ìíîïīǐ":
        return 'i'
    if char.lower() in "ýỳÿȳ":
        return 'y'
    return char

def deleteChars(text, chars):
    for c in chars:
        text = text.replace(c, "")
    return text


def cleanSynonym(text):
    text = text.replace("\r\n", " ").replace("\n", " ")
    text = text.replace("\t", " ")
    text = text.replace("-", " ")
    text = tagReg.sub(" ", text)
    text = re.sub(r"[^ a-zA-ZÀ-ÖØ-öø-ÿ]", "", text, flags=re.IGNORECASE)
    text = spaceReg.sub(" ", text)
    text = text.strip()
    return text


def expandBySynonyms(text, synonyms):
    if not synonyms:
        return text
    textLower = text.lower()
    found = []
    for sList in synonyms:
        for syn in sList:
            if " " + syn.lower() + " " in textLower or syn.lower() == textLower:
                found += [s for s in sList if s != syn]
                break
            
    if found:
        return  text + " " + " ".join(found)
    return text


def get_stamp():
    return  str(random.randint(0, 999999999))


def remove_fields(text, field_ords):
    return "\u001f".join([t for i,t in enumerate(text.split("\u001f")) if i not in field_ords])
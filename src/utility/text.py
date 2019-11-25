import re
from datetime import datetime
import time
import random

cleanWordReg = re.compile(u"^[^a-zA-Z0-9À-ÖØ-öø-ÿāōūēīȳǒǎǐě\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]*(\S+?)[^a-zA-Z0-9À-ÖØ-öø-ÿāōūēīȳǒǎǐě\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]*$", re.I |re.U)    
ignoreReg = re.compile(u"^[^a-zA-Z0-9À-ÖØ-öø-ÿǒāōūēīȳǒǎǐě\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]+$", re.I | re.U)
nonWordReg = re.compile(u"[^a-zA-Z0-9À-ÖØ-öø-ÿāōūēīȳǒǎǐě\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]", re.I | re.U) 
tagReg = re.compile(r'<[^>]+>|&nbsp;', flags = re.I)
spaceReg = re.compile('\s{2,}')
normalChar = re.compile(u"[a-z0-9öäü\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]", re.I | re.U) 
chineseChar = re.compile(u"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]", re.U)
non_weird_char = re.compile(u"[.;,-:_+*#?!\"'a-z0-9À-ÖØ-öø-ÿāōūēīȳǒǎǐě]", re.I | re.U)

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
        #this will prevent indexing / searching for base64 data urls
        if len(token) > 200:
            continue
        if ignoreReg.match(token) is not None:
            continue
        cleaned = cleanWordReg.sub(r'\1', token.strip())
        if (len(cleaned) <= 1 and not chineseChar.search(cleaned)) or cleaned.lower() in stopWords:
            continue
        filtered += cleaned + " "
    if len(filtered) > 0:
        return filtered[:-1]
    return ""


def trim_if_longer_than(text, n):
    if len(text) <= n:
        return text
    return text[:n] + "..."

def replace_vowels_with_accented_regex(text):
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

def replace_accents_with_vowels(text):
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

def text_too_small(text):
    if len(text) > 1:
        return False
    if len(text) == 0:
        return True
    if chineseChar.search(text):
        return False
    return True

def is_chinese_char(char):
    return chineseChar.match(char)


def ascii_fold_char(char):
    char = char.lower()
    if normalChar.match(char):
        return char
    if char in "àáâãåāăǎ":
        return 'a'
    if char in "ùúûūǔ":
        return 'u'
    if char in "òóôōǒ":
        return 'o'
    if char in "èéêëēěę":
        return 'e'
    if char in "ìíîïīǐ":
        return 'i'
    if char in "ýỳÿȳ":
        return 'y'
    return char

def delete_chars(text, chars):
    for c in chars:
        text = text.replace(c, "")
    return text


def clean_synonym(text):
    text = text.replace("\r\n", " ").replace("\n", " ")
    text = text.replace("\t", " ")
    text = text.replace("-", " ")
    text = tagReg.sub(" ", text)
    text = re.sub(r"[^ a-zA-ZÀ-ÖØ-öø-ÿ]", "", text, flags=re.IGNORECASE)
    text = spaceReg.sub(" ", text)
    text = text.strip()
    return text


def expand_by_synonyms(text, synonyms):
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


def clean_user_note_text(text):
    if text is None:
        return ""
    orig = text
    try:
        if text.startswith("<!DOCTYPE"):
            starting_html_ix = text.lower().find("</head><body ")
            if starting_html_ix > 0 and starting_html_ix < 300:
                text = text[starting_html_ix + 10:] 
                text = text[text.find(">") +1:]
                if text.lower().endswith("</body></html>"):
                    text = text[:-len("</body></html>")]
        # <script>
        text = re.sub("</?script[^>]?>", "", text)
        # <canvas>
        text = re.sub("<canvas[^>]{1,20}?>", "", text)
        # <a>
        text = re.sub("(<a [^>]*?href=(\".+?\"|'.+?')[^>]*?>|</a>)", "", text)
        text = re.sub("<a( [^>]{0,100}?)?>", "", text)

        # don't allow too large headers
        text = re.sub("<h[12]([> ])", "<h3 \1", text)
        text = re.sub("</h[12]>", "</h3>", text)

        text = text.replace("`", "&#96;").replace("$", "&#36;")

        text = text.replace("-qt-block-indent:0;", "")
        text = text.replace("-qt-paragraph-type:empty;", "")
        text = re.sub("<p style=\" ?margin-top:0px; margin-bottom:0px;", "<p style=\"", text) 

        #delete fonts and font sizes 
        text = re.sub("font-size:[^;\"']{1,10}?([;\"'])", "\1", text)
        text = re.sub("font-family:[^;]{1,40}?;", "", text)
        
        if len(orig) > 200 and len(text) == 0:
            return orig
        return text
    except:
        return orig

def remove_colors(text):
    #delete colors
    text = re.sub("(;|\"|') *color:[^;]{1,25};", "\1;", text)
    text = re.sub("(;|\"|') *background(-color)?:[^;]{1,25};", "\1;", text)
    text = re.sub(" bgcolor=\"[^\"]+\"", " ", text)
    return text
    
def build_user_note_text(title, text, source):
    """
    The index only has one field for the note content, so we have to collapse the note's fields
    into one string, similar to how regular note fields are distinguished with "\u001f".
    """
    return title + "\u001f" + text + "\u001f" + source

def remove_fields(text, field_ords):
    return "\u001f".join([t for i,t in enumerate(text.split("\u001f")) if i not in field_ords])


def remove_divs(html, replacement = ""):
    return re.sub("</?div ?[^>]*?>", replacement, html, flags=re.IGNORECASE)

def remove_tags(html, tags):
    return re.sub("</?(%s) ?[^>]*?>" % "|".join(tags), "", html, flags=re.IGNORECASE)

def remove_headers(html):
    html = re.sub("</?h[123456]( [^>]*?)?>", "", html, flags=re.IGNORECASE)
    html = re.sub("font-size: ?large;?", "", html, flags=re.IGNORECASE)
    return html

def remove_all_bold_formatting(html):
    orig = html
    #remove <b>
    html = re.sub("</?b( [^>]*?)?>", "", html, flags=re.IGNORECASE)
    #remove font-weight styles
    html = re.sub("font-weight: ?(bold|600|700|800|900);?", "", html, flags=re.IGNORECASE)
    if len(orig) > 50 and len(html) == 0:
        return orig
    return html

def find_all_images(html):
    """
    Returns a list of all <img> tags contained in the html.
    """
    return re.findall("<img[^>]*?>", html, flags=re.IGNORECASE) 

def escape_html(text):
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace("`", "&#96;")
    return text


def strip_url(url):
    url = re.sub("https?://(www\\.)?", "", url, re.I)
    return url

def clean_file_name(name):
    name = re.sub("[^a-zA-Z]", "-", name)
    return name


def try_find_sentence(text, selection):
    if not selection in text:
        return None
    selection = re.sub("  +", " ", selection).strip()
    text = re.sub("  +", " ", text).strip()
    last = text.rindex(selection)
    pre = text[:last]
    
    def _try_find_closing(text):
        found = False
        for c in [".", "!", "?", "•", ":", "=", "#", "-", "§", "Ø"]:
            try:
                if text.rindex(c) >= 0 and text.rindex(c) < len(text) -1:
                    text = text[text.rindex(c) + 1:]
                    found = True
                    break
            except:
                continue
        if not found: 
            return None
        return text
    
    
    pre = _try_find_closing(pre)
    if pre is None:
        return None
    after = text[last:]
    after = _try_find_closing(after[::-1])
    if after is None: 
        return None
    return pre + after[::-1] + "."

   
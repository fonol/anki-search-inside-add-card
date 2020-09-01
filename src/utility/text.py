# anki-search-inside-add-card
# Copyright (C) 2019 - 2020 Tom Z.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import re
from datetime import datetime
import time
import random
from bs4 import BeautifulSoup
import typing

cleanWordReg    = re.compile(u"^[^a-zA-Z0-9À-ÖØ-öø-ÿāōūēīȳǒǎǐě\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f\u3131-\uD79D\u0621-\u064A]*(\S+?)[^a-zA-Z0-9À-ÖØ-öø-ÿāōūēīȳǒǎǐě\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f\u3131-\uD79D\u0621-\u064A]*$", re.I |re.U)    
ignoreReg       = re.compile(u"^[^a-zA-Z0-9À-ÖØ-öø-ÿǒāōūēīȳǒǎǐě\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f\u3131-\uD79D\u0621-\u064A]+$", re.I | re.U)
nonWordReg      = re.compile(u"[^a-zA-Z0-9À-ÖØ-öø-ÿāōūēīȳǒǎǐě\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f\u3131-\uD79D\u0621-\u064A]", re.I | re.U) 
wordToken       = re.compile(u"[a-zA-Z0-9À-ÖØ-öø-ÿāōūēīȳǒǎǐě\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f\u3131-\uD79D\u0621-\u064A]", re.I | re.U)

# used to merge multiple field separator signs into singles 
SEP_RE          = re.compile(r'(?:\u001f){2,}|(?:\u001f[\s\r\n]+\u001f)')

# used to hide IO fields
IO_REPLACE      = re.compile('<img src="[^"]+(-\d+-Q|-\d+-A|-(<mark>)?oa(</mark>)?-[OA]|-(<mark>)?ao(</mark>)?-[OA])\.svg" ?/?>(</img>)?')

# move images in own line
IMG_FLD         = re.compile('\\|</span> ?(<img[^>]+/?>)( ?<span class=\'fldSep\'>|$)')

# hide cloze brackets
CLOZE_REPLACE   = re.compile(r"{{c\d+::([^}]*?)(?:::[^}]+)?}}")

tagReg          = re.compile(r'<[^>]+>|&nbsp;', flags = re.I)
spaceReg        = re.compile('\s{2,}')
normalChar      = re.compile(u"[a-z0-9öäü\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f\u3131-\uD79D]", re.I | re.U) 

asian_or_arabic_char    = re.compile(u"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f\u3131-\uD79D\u0621-\u064A]", re.U)
asian_char              = re.compile(u"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f\u3131-\uD79D]", re.U)

def clean(text, stopWords):

    filtered    = ""
    text        = text.replace("`", "")
    text        = text.replace("\r\n", " ").replace("\n", " ")
    text        = text.replace("\t", " ")
    text        = text.replace("\u001f", " ")
    text        = tagReg.sub(" ", text)
    text        = nonWordReg.sub(" ", text)
    text        = spaceReg.sub(" ", text)
    stopWords   = [s.lower() for s in stopWords]

    for token in tokenize(text):
        #this will prevent indexing / searching for base64 data urls
        if len(token) > 200:
            continue
        if ignoreReg.match(token) is not None:
            continue
        cleaned = cleanWordReg.sub(r'\1', token.strip())
        if (len(cleaned) <= 1 and not asian_or_arabic_char.search(cleaned)) or cleaned.lower() in stopWords:
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
        if re.search(u'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f\u3131-\uD79D]', token):
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
    if asian_or_arabic_char.search(text):
        return False
    return True

def is_asian_or_arabic_char(char):
    """ Supported atm: chinese, japanese, korean, arabic """
    return asian_or_arabic_char.match(char)

def is_asian_char(char):
    """ Supported atm: chinese, japanese, korean """
    return asian_char.match(char)

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

        text = text.strip()
        # <script>
        text = re.sub("</?script[^>]?>", "", text)
        # <canvas>
        text = re.sub("<canvas[^>]{1,20}?>", "", text)
        # <a>
        text = re.sub("(<a [^>]*?href=(\".+?\"|'.+?')[^>]*?>|</a>)", "", text)
        text = re.sub("<a( [^>]{0,100}?)?>", "", text)

        # remove styles in <p>
        text = re.sub("<p style=\"[^\">]*\" ?>", "<p>", text)

        # remove trailing empty paragraphs 
        text = re.sub("^(?: |\r\n|\n)*(<p[^>]*>(?: |\r\n|\n)*<br ?/?>(?: |\r\n|\n)*</p>(?: |\r\n|\n)*)+", "", text)
        text = re.sub("^(?: |\r\n|\n)*(<p[^>]*>)(?: |\r\n|\n)*<br ?/?>", "\\1", text)
        text = re.sub("(<p[^>]*>(?: |\r\n|\n)*<br ?/?>( |\r\n|\n)*</p>(?: |\r\n|\n)*)+$", "", text)


        # represent indentation with &nbsp;
        text = text.replace("\t", "&nbsp;"*4)
        while re.match(r"(<p>(?:<br ?/?>|\n|\r\n)?(?:&nbsp;)*)\s", text):
            text = re.sub(r"(<p>(?:<br ?/?>|\n|\r\n)?(?:&nbsp;)*)\s", r"\1&nbsp;", text)

        # don't allow too large headers
        text = re.sub("<h[12]([> ])", "<h3 \\1", text)
        text = re.sub("</h[12]>", "</h3>", text)

        text = text.replace("`", "&#96;").replace("$", "&#36;")

        text = text.replace("-qt-block-indent:0;", "")
        text = text.replace("-qt-paragraph-type:empty;", "")

        # delete fonts and font sizes 
        text = re.sub("font-size:[^;\"']{1,10}?([;\"'])", "\\1", text)
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
    return re.sub("</?(%s) ?[^>]{0,200}?>" % "|".join(tags), "", html, flags=re.IGNORECASE)

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

def html_to_text(html):

    try:
        soup = BeautifulSoup(html, features="html.parser")
        text = ""
        for d in soup.descendants:
            if isinstance(d, str):
                text += d.strip()
            elif d.name in ["br", "h1", "h2", "h3", "h4", "h5", "h6", "p"]:
                text += '\n'
        return text.strip()
    except:
        return html
 

def escape_html(text):
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace("`", "&#96;")
    return text

def strip_url(url):
    url = re.sub("https?://(www\\.)?", "", url, re.I)
    return url
        
def clean_user_note_title(title):
    if title is None:
        return ""
    title = title.replace("\r\n", "")
    title = title.replace("\n", "")
    title = title.replace("\t", "")
    return title

def cleanFieldSeparators(text):
    text = SEP_RE.sub("\u001f", text)
    if text.endswith("\u001f"):
        text = text[:-1]
    text = text.replace("\u001f", "<span class='fldSep'>|</span>")
    text = re.sub(r"((?:</li>(?:\n| )*)?</(?:p|div|ul|ol)>|<br/?>)(?:\n| )*<span class=['\"]fldSep['\"]>\|</ ?span>", r"<span class='fldSep'>|</span>\1", text)
    # text = text.replace("</p><span class='fldSep'>|</span><p>", "<span class='fldSep'>|</span></p><p>")
    return text

def newline_before_images(text):
    return IMG_FLD.sub("|</span><br/>\\1<br/>\\2", text)

def try_hide_image_occlusion(text):
    """
    Image occlusion cards take up too much space, so we try to hide all images except for the first.
    """
    if not text.count("<img ") > 1:
        return text
    text = IO_REPLACE.sub("(IO - image hidden)", text)
    return text

def hide_cloze_brackets(text): 
    """ {{clozed text}} -> clozed text """
    if not text:
        return ""
    return CLOZE_REPLACE.sub("\\1", text)

def is_html(text: str) -> bool:
    """ Guess if given text contains html. Not really comprehensive. """

    if not text or len(text.strip()) == 0:
        return False
    if re.search(r"< ?/ ?(?:p|b|em|a|div|i|h[123456]|strong|img|pre|span|code|html|input|script|style|label|button|font)>", text[:200], re.IGNORECASE):
        return True
    return False


def clean_file_name(name):
    name = re.sub("[^a-zA-Z0-9]", "-", name)
    return name

def remove_special_chars(text):
    text = re.sub("[.;,\"'?!:\\-=§$%&/()\\[\\]{}\n`#~+|]", "", text)
    return text

def try_find_sentence(text, selection):
    if not selection in text:
        return None

    selection   = re.sub("  +", " ", selection).strip()
    text        = re.sub("  +", " ", text).strip()
    last        = text.rindex(selection)
    pre         = text[:last]
    
    def _try_find_closing(text):
        found = False
        for c in ["\\.\\B", "!", "\\?", "•", ":", "=", "#", "-", "§", "Ø", "\\*"]:
            try:
                found = [(i.start()) for i in re.finditer(c,text)]
                if len(found) > 0:
                    last_index = found[-1]
                    if last_index < len(text) - 1:
                        text = text[last_index + 1]
                        found = True
                        break
            except:
                continue
        if not found: 
            if len(text) < 50:
                return text
            return None
        return text
    
    
    pre         = _try_find_closing(pre)
    if pre is None:
        return None
    after       = text[last:]
    after       = _try_find_closing(after[::-1])
    if after is None: 
        return None

    return pre + after[::-1] + "."

def set_yt_time(src: str, time: int) -> str:
    id = get_yt_video_id(src)
    return f"https://www.youtube.com/watch?v={id}&t={time}s"

def get_yt_video_id(src: str) -> str:
    match = re.match(r".+/watch\?v=([^&]+)(?:&t=.+)?", src)
    if match: 
        return match.group(1)
    return ""


   
def clean_tags(tags):
    if tags is None or len(tags.strip()) == 0:
        return ""
    
    tags = re.sub("[`'\"]", "", tags)
    return tags


def mark_highlights(text, querySet):

    currentWord             = ""
    currentWordNormalized   = ""
    textMarked              = ""
    lastIsMarked            = False
    # c = 0
    for char in text:
        # c += 1
        if wordToken.match(char):
            currentWordNormalized = ''.join((currentWordNormalized, ascii_fold_char(char).lower()))
            # currentWordNormalized = ''.join((currentWordNormalized, char.lower()))
            if is_asian_char(char) and str(char) in querySet:
                currentWord = ''.join((currentWord, "<MARK>%s</MARK>" % char))
            else:
                currentWord = ''.join((currentWord, char))

        else:
            #we have reached a word boundary
            #check if word is empty
            if currentWord == "":
                textMarked = ''.join((textMarked, char))
            else:
                #if the word before the word boundary is in the query, we want to highlight it
                if currentWordNormalized in querySet:
                    #we check if the word before has been marked too, if so, we want to enclose both, the current word and
                    # the word before in the same <mark></mark> tag (looks better)
                    if lastIsMarked and not "\u001f" in textMarked[textMarked.rfind("<MARK>"):]:
                    # if lastIsMarked:
                        closing_index   = textMarked.rfind("</MARK>")
                        textMarked      = ''.join((textMarked[0: closing_index], textMarked[closing_index + 7 :]))
                        textMarked      = ''.join((textMarked, currentWord, "</MARK>", char))
                    else:
                        textMarked      = ''.join((textMarked, "<MARK>", currentWord, "</MARK>", char))
                        # c += 13
                    lastIsMarked = True
                #if the word is not in the query, we simply append it unhighlighted
                else:
                    textMarked      = ''.join((textMarked, currentWord, char))
                    lastIsMarked    = False

                currentWord             = ""
                currentWordNormalized   = ""

    if currentWord != "":
        if currentWord != "MARK" and currentWordNormalized in querySet:
            textMarked = ''.join((textMarked, "<MARK>", currentWord, "</MARK>"))
        else:
            textMarked = ''.join((textMarked, currentWord))

    return textMarked
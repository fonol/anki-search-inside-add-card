use base64;
use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use std::fs::{read, File};
use std::collections::HashSet;
use std::fmt::format;
#[macro_use] extern crate lazy_static;
use regex::Regex;

lazy_static! {
    static ref word_token : Regex = Regex::new(r"[a-zA-Z0-9À-ÖØ-öø-ÿāōūēīȳǒǎǐě\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f\u3131-\uD79D\u0621-\u064A]").unwrap();
    static ref asian_char : Regex = Regex::new(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f\u3131-\uD79D]").unwrap();
    static ref default_char : Regex = Regex::new(r"[a-z0-9öäü\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f\u3131-\uD79D]").unwrap();
}


#[pyfunction]
fn encode_file(_py: Python, file: &str) -> PyResult<String> {
    return Ok(base64::encode(read(file).unwrap()));
}

fn _is_asian_char(c: char) -> bool {
    asian_char.is_match(&c.to_string())
}
fn _ascii_fold_char(c: char) -> char {
    let as_str = c.to_string().to_lowercase();
    if default_char.is_match(&as_str) {
        return c;
    }
    if "àáâãåāăǎ".contains(&as_str) {
        return 'a';
    }
    if "ùúûūǔ".contains(&as_str) {
        return 'u';
    }
    if "òóôōǒ".contains(&as_str) {
        return 'o';
    }
    if "èéêëēěę".contains(&as_str) {
        return 'e';
    }
    if "ìíîïīǐ".contains(&as_str) {
        return 'i';
    }
    if "ýỳÿȳ".contains(&as_str) {
        return 'y';
    }
    c
}

#[pyfunction]
fn rs_mark_highlights(_py: Python, text: &str, query_set: Vec<String>) -> PyResult<String> {

    let mut current_word = String::new();
    let mut current_word_normalized = String::new();
    let mut text_marked = String::new();
    let mut last_is_marked = false;

    let mut cstr : String = String::new();

    for c in text.chars() {
        cstr = c.to_string();
        if word_token.is_match(&cstr) {
            current_word_normalized.push(_ascii_fold_char(c));
            if _is_asian_char(c) && query_set.contains(&c.to_string()) {
                current_word.push_str(&format!("<MARK>{}</MARK>", c));
            } else {
                current_word.push(c);
            }
        } else {
            if current_word.is_empty() {
                text_marked.push(c);
            } else {
                if query_set.contains(&current_word_normalized){
                    if last_is_marked && ! text_marked[text_marked.rfind("<MARK>").unwrap()..].contains(r"\u001f") {
                        let closing_index = text_marked.rfind("</MARK>").unwrap();
                        text_marked = String::from([&text_marked[0..closing_index], &text_marked[closing_index+7..]].concat());
                        text_marked.push_str(&current_word);
                        text_marked.push_str("</MARK>");
                        text_marked.push(c);
                    } else {
                        text_marked.push_str("<MARK>");
                        text_marked.push_str(&current_word);
                        text_marked.push_str("</MARK>");
                        text_marked.push(c);
                    }
                    last_is_marked = true;
                } else {
                    text_marked.push_str(&current_word);
                    text_marked.push(c);
                    last_is_marked = false;
                }

                current_word.clear();
                current_word_normalized.clear();
            }
        }
    }
    if !current_word.is_empty() {
        if current_word != "MARK" && query_set.contains(&current_word_normalized) {
            text_marked.push_str("<MARK>");
            text_marked.push_str(&current_word);
            text_marked.push_str("</MARK>");
        } else {
            text_marked.push_str(&current_word);
        }
    }

    return Ok(text_marked);

}


#[pymodule]
fn siacrs(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_wrapped(wrap_pyfunction!(encode_file))?;
    m.add_wrapped(wrap_pyfunction!(rs_mark_highlights))?;

    Ok(())
}


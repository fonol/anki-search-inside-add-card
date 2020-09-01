use base64;
use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use std::fs::{read, File};

#[pyfunction]
fn encode_file(_py: Python, file: &str) -> PyResult<String> {
    return Ok(base64::encode(read(file).unwrap()));
}
#[pymodule]
fn siacrs(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_wrapped(wrap_pyfunction!(encode_file))?;

    Ok(())
}

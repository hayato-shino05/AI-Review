use std::ffi::CString;
use std::os::raw::c_char;

fn to_str(ptr: *const c_char, len: usize) -> String {
    if ptr.is_null() || len == 0 {
        return String::new();
    }
    let bytes = unsafe { std::slice::from_raw_parts(ptr as *const u8, len) };
    String::from_utf8_lossy(bytes).into_owned()
}

#[no_mangle]
pub extern "C" fn shino_score_file(
    filename_ptr: *const c_char,
    filename_len: usize,
    patch_ptr: *const c_char,
    patch_len: usize,
) -> i32 {
    let name = to_str(filename_ptr, filename_len).to_ascii_lowercase();
    let patch = to_str(patch_ptr, patch_len).to_ascii_lowercase();
    let combined = format!("{} {}", name, patch);

    let mut score: i32 = 0;

    let sensitive = [
        "auth", "security", "crypto", "token", "jwt", "oauth", "session",
        "permission", "rbac", "secret", "password", "sql", "migration",
        "unsafe", "mutex", "atomic", "lock", "eval(", "exec(",
    ];
    if sensitive.iter().any(|kw| combined.contains(*kw)) {
        score += 100;
    }

    let tier = [
        "controller", "route", "api", "handler", "middleware", "service",
        "db", "repository", "webhook", "kernel",
    ];
    if tier.iter().any(|t| combined.contains(*t)) {
        score += 60;
    }

    let src_ext = [".py", ".ts", ".tsx", ".rs", ".cpp", ".hpp", ".go", ".java", ".cs", ".js"];
    if src_ext.iter().any(|e| name.ends_with(e)) {
        score += 30;
    }

    let is_test = name.starts_with("test_")
        || name.contains("_test")
        || name.contains(".spec.")
        || name.contains("/tests/");
    if is_test {
        score += 10;
    }

    let doc_ext = [".md", ".txt", ".lock", ".svg"];
    if doc_ext.iter().any(|e| name.ends_with(e)) || name.contains("package-lock") {
        score -= 50;
    }

    score
}

#[no_mangle]
pub extern "C" fn shino_estimate_tokens(ptr: *const c_char, len: usize) -> usize {
    let s = to_str(ptr, len);
    let bytes = s.as_bytes();
    let mut count: usize = 0;
    let mut in_word = false;
    for &b in bytes {
        let is_word = matches!(b, b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'_');
        if is_word {
            if !in_word {
                count += 1;
                in_word = true;
            }
        } else if b == b' ' || b == b'\t' || b == b'\n' || b == b'\r' {
            in_word = false;
        } else {
            count += 1;
            in_word = false;
        }
    }
    count
}

fn cstr_into_raw(s: String) -> *mut c_char {
    match CString::new(s) {
        Ok(c) => c.into_raw(),
        Err(_) => CString::new("").unwrap().into_raw(),
    }
}

#[no_mangle]
pub extern "C" fn shino_repair_yaml(ptr: *const c_char, len: usize) -> *mut c_char {
    let input = to_str(ptr, len);
    cstr_into_raw(repair_yaml(&input))
}

const MULTILINE_KEYS: [&str; 2] = ["issue_content", "security_concerns"];

fn flush(collecting: &mut Option<String>, collected: &mut Vec<String>, out: &mut Vec<String>) {
    if let Some(key) = collecting.take() {
        if collected.is_empty() {
            out.push(format!("{}:", key));
        } else {
            out.push(format!("{}: \"{}\"", key, collected.join(" ")));
        }
        collected.clear();
    }
}

fn process_key_line(
    line: &str,
    collecting: &mut Option<String>,
    out: &mut Vec<String>,
) {
    if let Some(idx) = line.find(':') {
        let key = line[..idx].trim();
        let val = line[idx + 1..].trim();
        if val.is_empty() && MULTILINE_KEYS.contains(&key) {
            *collecting = Some(key.to_string());
        } else {
            out.push(line.to_string());
        }
    } else {
        out.push(line.to_string());
    }
}

fn repair_yaml(input: &str) -> String {
    let mut out: Vec<String> = Vec::new();
    let mut in_fence = false;
    let mut started = false;
    let mut collecting: Option<String> = None;
    let mut collected: Vec<String> = Vec::new();

    for raw in input.lines() {
        let trimmed = raw.trim();

        if trimmed.starts_with("```") {
            in_fence = !in_fence;
            continue;
        }
        if in_fence {
            continue;
        }
        if trimmed == "---" || trimmed == "..." {
            continue;
        }

        if !started {
            if trimmed.is_empty() {
                continue;
            }
            if trimmed.contains(':') || trimmed.starts_with('-') {
                started = true;
            } else {
                continue; // preamble text before the YAML block
            }
        }

        if trimmed.is_empty() {
            flush(&mut collecting, &mut collected, &mut out);
            out.push(String::new());
            continue;
        }

        // Trailing explanation text (prose without YAML structure) ends the block,
        // unless we are inside a multiline value collection.
        if collecting.is_none()
            && !trimmed.starts_with(' ')
            && !trimmed.starts_with('-')
            && !trimmed.contains(':')
        {
            break;
        }

        let line = fix_line(trimmed);

        if let Some(ref _key) = collecting {
            // Inside a multiline value collection.
            if line.starts_with('-') {
                flush(&mut collecting, &mut collected, &mut out);
                out.push(line);
                continue;
            }
            if line.contains(':') && !line.starts_with(' ') {
                // A new top-level key begins: flush the collected value first.
                flush(&mut collecting, &mut collected, &mut out);
                process_key_line(&line, &mut collecting, &mut out);
                continue;
            }
            // Unindented continuation line -> append to the collected value.
            collected.push(line);
            continue;
        }

        process_key_line(&line, &mut collecting, &mut out);
    }

    flush(&mut collecting, &mut collected, &mut out);
    out.join("\n")
}

fn fix_line(line: &str) -> String {
    let mut t = line.trim().to_string();
    // -item -> - item  (list dash missing its space)
    if let Some(rest) = t.strip_prefix('-') {
        if !rest.starts_with(' ') && !rest.is_empty() {
            t = format!("- {}", rest.trim_start());
        }
    }

    // key: value  -> quote unquoted values that contain ": " or "#".
    // A value that already starts with a single quote cannot safely stay raw
    // (e.g. 'nested' quote inside breaks PyYAML), so re-wrap it in double quotes.
    if let Some(idx) = t.find(':') {
        let key = t[..idx].trim();
        let val = t[idx + 1..].trim();
        if !val.is_empty()
            && !val.starts_with('"')
            && (val.contains(": ") || val.contains('#') || val.starts_with('\''))
        {
            let inner = val.trim_start_matches('\'').trim_end_matches('\'');
            t = format!("{}: \"{}\"", key, inner);
        }
    }

    t
}

#[no_mangle]
pub extern "C" fn shino_extract_defs(ptr: *const c_char, len: usize) -> *mut c_char {
    let input = to_str(ptr, len);
    cstr_into_raw(extract_defs(&input))
}

fn extract_defs(input: &str) -> String {
    let mut names: Vec<String> = Vec::new();
    for raw in input.lines() {
        // Drop diff prefixes (+ / - / context space) before scanning.
        let t = raw
            .trim_start()
            .trim_start_matches(&['+', '-', ' '][..])
            .trim_start()
            .to_string();
        if let Some(name) = extract_one(&t) {
            names.push(name);
        }
    }
    if names.is_empty() {
        return String::new();
    }
    names.join("\n") + "\n"
}

fn extract_one(t: &str) -> Option<String> {
    let patterns = [
        "export function ", "export const ", "fn ", "func ", "def ", "class ",
        "struct ", "enum ", "interface ", "type ",
    ];
    for prefix in patterns {
        if let Some(rest) = t.strip_prefix(prefix) {
            let name: String = rest
                .chars()
                .take_while(|c| c.is_alphanumeric() || *c == '_')
                .collect();
            if !name.is_empty() {
                return Some(name);
            }
        }
    }
    None
}

#[no_mangle]
pub extern "C" fn shino_free_str(ptr: *mut c_char) {
    if ptr.is_null() {
        return;
    }
    unsafe {
        drop(CString::from_raw(ptr));
    }
}

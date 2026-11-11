use std::collections::HashSet;
use std::ffi::CString;
use std::os::raw::c_char;

const US: char = '\u{1f}';

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

    // key: value  -> quote unquoted values that contain ': ' or '#'.
    // Tim dau hai chua key/value bo qua toan tu scope :: (C++/Rust) nhan vao
    // std::shared_lock, storage::cache::BlockCache, crc32fast::Hasher.
    let bytes = t.as_bytes();
    let key_colon = bytes.iter().position(|&b| b == b':').filter(|&i| {
        let prev_ok = i == 0 || bytes[i - 1] != b':';
        let next_ok = i + 1 == bytes.len() || bytes[i + 1] != b':';
        prev_ok && next_ok
    });
    let Some(idx) = key_colon else { return t; };
    let key = t[..idx].trim();
    let val = t[idx + 1..].trim();
    if !val.is_empty()
        && !val.starts_with('"')
        && (val.contains(": ") || val.contains('#') || val.starts_with('\''))
    {
        let inner = val.trim_start_matches('\'').trim_end_matches('\'');
        t = format!("{}: \"{}\"", key, inner);
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

// ---------------------------------------------------------------------------
// Cubic Filtering Agent: Hallucination + Suppression + Noise/Dedupe
//
// Input payload is line-based, fields separated by 0x1f (unit separator):
//   P\x1f<profile>                                    profile: chill|balanced|assertive
//   H\x1f<file>\x1f<start_line>\x1f<end_line>         diff hunk (real changed lines)
//   S\x1f<file>\x1f<keyword>                          developer-suppressed pair
//   F\x1f<idx>\x1f<file>\x1f<start>\x1f<end>\x1f<sev>\x1f<header>\x1f<content>
// Output: comma-separated kept finding idx values, e.g. "0,2,3"
// ---------------------------------------------------------------------------

const VAGUE: [&str; 6] = [
    "consider checking", "might want to", "could potentially", "maybe", "nit:", "cân nhệc kiểm tra",
];

struct Finding {
    idx: usize,
    file: String,
    start: usize,
    end: usize,
    severity: String,
    header: String,
    content: String,
}

fn sev_rank(s: &str) -> u8 {
    match s {
        "P0" => 0,
        "P1" => 1,
        "P2" => 2,
        "P3" => 3,
        _ => 4,
    }
}

#[no_mangle]
pub extern "C" fn shino_filter_findings(
    payload_ptr: *const c_char,
    payload_len: usize,
) -> *mut c_char {
    let payload = to_str(payload_ptr, payload_len);
    cstr_into_raw(filter_findings(&payload))
}

fn filter_findings(payload: &str) -> String {
    let mut profile = String::new();
    let mut hunks: Vec<(String, usize, usize)> = Vec::new();
    let mut suppressed: Vec<(String, String)> = Vec::new();
    let mut findings: Vec<Finding> = Vec::new();

    for line in payload.lines() {
        if line.is_empty() {
            continue;
        }
        let parts: Vec<&str> = line.split(US).collect();
        if parts.is_empty() {
            continue;
        }
        match parts[0] {
            "P" => {
                if parts.len() > 1 {
                    profile = parts[1].to_string();
                }
            }
            "H" => {
                if parts.len() >= 4 {
                    if let (Ok(s), Ok(e)) =
                        (parts[2].parse::<usize>(), parts[3].parse::<usize>())
                    {
                        hunks.push((parts[1].to_string(), s, e));
                    }
                }
            }
            "S" => {
                if parts.len() >= 3 {
                    suppressed.push((parts[1].to_string(), parts[2].to_string()));
                }
            }
            "F" => {
                if parts.len() >= 8 {
                    findings.push(Finding {
                        idx: parts[1].parse::<usize>().unwrap_or(0),
                        file: parts[2].to_string(),
                        start: parts[3].parse::<usize>().unwrap_or(0),
                        end: parts[4].parse::<usize>().unwrap_or(0),
                        severity: parts[5].to_string(),
                        header: parts[6].to_string(),
                        content: parts[7].to_string(),
                    });
                }
            }
            _ => {}
        }
    }

    let mut kept: Vec<usize> = Vec::new(); // array indices into findings

    for (i, f) in findings.iter().enumerate() {
        // 1. Hallucination / diff-line grounding filter.
        let file_hunks: Vec<(usize, usize)> = hunks
            .iter()
            .filter(|(hf, _, _)| hf == &f.file)
            .map(|(_, s, e)| (*s, *e))
            .collect();
        let in_hunks = !file_hunks.is_empty();
        let near_hunk = file_hunks.iter().any(|(s, e)| {
            !(f.end < s.saturating_sub(20) || f.start > e + 20)
        });
        let is_security = f.severity == "P0"
            || f.header.to_ascii_lowercase().contains("security")
            || f.content.to_ascii_lowercase().contains("security");
        if !in_hunks || (!near_hunk && !is_security) {
            continue;
        }

        // 2. Suppression filter (developer learnings).
        if suppressed.iter().any(|(sf, kw)| {
            sf == &f.file && (f.header.contains(kw) || f.content.contains(kw))
        }) {
            continue;
        }

        // 3. Noise / profile filter.
        if profile != "assertive" {
            let text = format!("{} {}", f.header, f.content);
            let tl = text.to_ascii_lowercase();
            let vague = VAGUE.iter().any(|p| tl.contains(p));
            let short = (f.header.len() + f.content.len()) < 40;
            let remove = match profile.as_str() {
                "chill" => vague && short && (f.severity == "P3" || f.severity == "P2"),
                "balanced" => vague && short && f.severity == "P3",
                _ => false,
            };
            if remove {
                continue;
            }
        }

        kept.push(i);
    }

    // 4. Overlap deduplication filter.
    let mut keep_set: HashSet<usize> = kept.iter().cloned().collect();
    for a in 0..kept.len() {
        if !keep_set.contains(&kept[a]) {
            continue;
        }
        for b in (a + 1)..kept.len() {
            let i = kept[a];
            let j = kept[b];
            let fa = &findings[i];
            let fb = &findings[j];
            if fa.file != fb.file {
                continue;
            }
            let overlap = fa.start <= fb.end + 2 && fb.start <= fa.end + 2;
            let same_header = fa.header == fb.header;
            if overlap || same_header {
                let ra = sev_rank(&fa.severity);
                let rb = sev_rank(&fb.severity);
                if ra < rb {
                    keep_set.remove(&j);
                } else if rb < ra {
                    keep_set.remove(&i);
                } else {
                    keep_set.remove(&j); // tie: keep the earlier one
                }
            }
        }
    }

    let mut result: Vec<usize> = kept
        .into_iter()
        .filter(|i| keep_set.contains(i))
        .map(|i| findings[i].idx)
        .collect();
    result.sort_unstable();
    result
        .iter()
        .map(|i| i.to_string())
        .collect::<Vec<_>>()
        .join(",")
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

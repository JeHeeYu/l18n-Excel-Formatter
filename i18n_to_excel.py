import csv
import os
import re


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
LOCALES_DIR = os.path.join(PROJECT_ROOT, "src", "shared", "i18n", "locales")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "다국어_번역.csv")
LOCALE_FILES = [
    ("ko", os.path.join(LOCALES_DIR, "ko.ts")),
    ("en", os.path.join(LOCALES_DIR, "en.ts")),
    ("vn", os.path.join(LOCALES_DIR, "vn.ts")),
    ("np", os.path.join(LOCALES_DIR, "np.ts")),
    ("th", os.path.join(LOCALES_DIR, "th.ts")),
    ("kh", os.path.join(LOCALES_DIR, "kh.ts")),
    ("mn", os.path.join(LOCALES_DIR, "mn.ts")),
    ("cn", os.path.join(LOCALES_DIR, "cn.ts")),
    ("uz", os.path.join(LOCALES_DIR, "uz.ts")),
]


def load_locale_object_literal(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as file:
        source = file.read()

    match = re.search(
        r"const\s+\w+\s*=\s*(\{[\s\S]*\})\s+as const\s+export default\s+\w+\s*$",
        source,
    )
    if match:
        return match.group(1)

    raise ValueError(f"Failed to parse locale file: {file_path}")


def skip_whitespace(text: str, index: int) -> int:
    while index < len(text) and text[index].isspace():
        index += 1
    return index


def parse_string(text: str, index: int):
    quote = text[index]
    index += 1
    chars = []

    while index < len(text):
        char = text[index]
        if char == "\\":
            index += 1
            if index >= len(text):
                break
            escaped = text[index]
            escape_map = {
                "n": "\n",
                "r": "\r",
                "t": "\t",
                "\\": "\\",
                "'": "'",
                '"': '"',
            }
            chars.append(escape_map.get(escaped, escaped))
            index += 1
            continue
        if char == quote:
            return "".join(chars), index + 1
        chars.append(char)
        index += 1

    raise ValueError("Unterminated string")


def parse_key(text: str, index: int):
    index = skip_whitespace(text, index)
    if text[index] in ("'", '"'):
        return parse_string(text, index)

    match = re.match(r"[A-Za-z0-9_]+", text[index:])
    if not match:
        raise ValueError(f"Invalid key at index {index}")
    key = match.group(0)
    return key, index + len(key)


def parse_value(text: str, index: int):
    index = skip_whitespace(text, index)
    char = text[index]

    if char == "{":
        return parse_js_object(text, index)
    if char in ("'", '"'):
        return parse_string(text, index)

    match = re.match(r"(true|false|null|-?\d+(?:\.\d+)?)", text[index:])
    if not match:
        raise ValueError(f"Unsupported value at index {index}")
    raw = match.group(0)
    next_index = index + len(raw)

    if raw == "true":
        return True, next_index
    if raw == "false":
        return False, next_index
    if raw == "null":
        return None, next_index
    if "." in raw:
        return float(raw), next_index
    return int(raw), next_index


def parse_js_object(text: str, start_index: int = 0):
    index = skip_whitespace(text, start_index)
    if text[index] != "{":
        raise ValueError("Object must start with '{'")
    index += 1
    result = {}

    while True:
        index = skip_whitespace(text, index)
        if text[index] == "}":
            return result, index + 1

        key, index = parse_key(text, index)
        index = skip_whitespace(text, index)
        if text[index] != ":":
            raise ValueError("Expected ':' after key")
        index += 1

        value, index = parse_value(text, index)
        result[key] = value

        index = skip_whitespace(text, index)
        if text[index] == ",":
            index += 1
            continue
        if text[index] == "}":
            return result, index + 1
        raise ValueError("Expected ',' or '}' in object")


def flatten_object(value, prefix=""):
    if not isinstance(value, dict):
        return [(prefix, value)]

    rows = []
    for key, nested_value in value.items():
        next_prefix = f"{prefix}.{key}" if prefix else key
        rows.extend(flatten_object(nested_value, next_prefix))
    return rows


def to_excel_text(value):
    text = "" if value is None else str(value)
    if text == "":
        return text
    return f"'{text}"


def main():
    locale_maps = {}
    all_keys = set()

    for locale, file_path in LOCALE_FILES:
        object_literal = load_locale_object_literal(file_path)
        parsed, _ = parse_js_object(object_literal)
        flattened = dict(flatten_object(parsed))
        locale_maps[locale] = flattened
        all_keys.update(flattened.keys())

    sorted_keys = sorted(all_keys, key=str.lower)

    with open(OUTPUT_PATH, "w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["variable", *[locale for locale, _ in LOCALE_FILES]])
        for key in sorted_keys:
            writer.writerow([
                to_excel_text(key),
                *[to_excel_text(locale_maps[locale].get(key, "")) for locale, _ in LOCALE_FILES],
            ])

    print(f"Exported {len(sorted_keys)} keys to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

"""
vvproj のモーラアノテーションと pyopenjtalk の出力（カタカナ読み）の不一致を、
人間が読みやすいテキストファイルとして出力する。

pyopenjtalk はテキストを入力に音素列（カタカナ）とアクセントを出力する。
本スクリプトは、同一テキストに対する pyopenjtalk の出力と vvproj のモーラ列を比較する。

出力:
1. mismatch_report_full.txt - 全不一致件
2. mismatch_report_rare_phonemes.txt - ROHAN に含まれるが VOICEVOX pyopenjtalk 非対応の
   音素（クァ, グァ, シィ, デェ, フュ）を含む件のみ

判定: pyopenjtalk の pron と vvproj のモーラ列を正規化後比較し、一致しないものを不一致とする。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

try:
    import pyopenjtalk
except ImportError:
    pyopenjtalk = None

# 長音 ー を直前の母音に展開するためのマッピング
VOWEL_MAP = {
    "ア": "ア", "イ": "イ", "ウ": "ウ", "エ": "エ", "オ": "オ",
    "ァ": "ア", "ィ": "イ", "ゥ": "ウ", "ェ": "エ", "ォ": "オ",
    "ャ": "ア", "ュ": "ウ", "ョ": "オ",
    "カ": "ア", "キ": "イ", "ク": "ウ", "ケ": "エ", "コ": "オ",
    "ガ": "ア", "ギ": "イ", "グ": "ウ", "ゲ": "エ", "ゴ": "オ",
    "サ": "ア", "シ": "イ", "ス": "ウ", "セ": "エ", "ソ": "オ",
    "ザ": "ア", "ジ": "イ", "ズ": "ウ", "ゼ": "エ", "ゾ": "オ",
    "タ": "ア", "チ": "イ", "ツ": "ウ", "テ": "エ", "ト": "オ",
    "ダ": "ア", "ヂ": "イ", "ヅ": "ウ", "デ": "エ", "ド": "オ",
    "ナ": "ア", "ニ": "イ", "ヌ": "ウ", "ネ": "エ", "ノ": "オ",
    "ハ": "ア", "ヒ": "イ", "フ": "ウ", "ヘ": "エ", "ホ": "オ",
    "バ": "ア", "ビ": "イ", "ブ": "ウ", "ベ": "エ", "ボ": "オ",
    "パ": "ア", "ピ": "イ", "プ": "ウ", "ペ": "エ", "ポ": "オ",
    "マ": "ア", "ミ": "イ", "ム": "ウ", "メ": "エ", "モ": "オ",
    "ヤ": "ア", "ユ": "ウ", "ヨ": "オ",
    "ラ": "ア", "リ": "イ", "ル": "ウ", "レ": "エ", "ロ": "オ",
    "ワ": "ア", "ヰ": "イ", "ヲ": "オ", "ン": "ン", "ッ": "ッ",
    "ヴ": "ウ", "フ": "ウ",
    "ギャ": "ア", "ギュ": "ウ", "ギョ": "オ",
    "クァ": "ア", "クィ": "イ", "クゥ": "ウ", "クェ": "エ", "クォ": "オ",
    "グァ": "ア", "グィ": "イ", "グゥ": "ウ", "グェ": "エ", "グォ": "オ",
    "シィ": "イ", "スィ": "イ", "ティ": "イ", "トゥ": "ウ",
    "デェ": "エ", "フュ": "ウ",
}

# VOICEVOX pyopenjtalk 非対応だが ROHAN4600 に含まれるレア音素
RARE_PHONEMES = ("クァ", "クィ", "クゥ", "クェ", "クォ", "グァ", "グィ", "グゥ", "グェ", "グォ", "シィ", "デェ", "フュ")


def normalize_for_comparison(kana: str) -> str:
    """比較用に正規化。句読点・無声化記号除去、ヲ→オ、長音展開。"""
    kana = re.sub(r"[、。？！\s\u0027\u2018\u2019\u02bc]", "", kana)
    kana = kana.replace("ヲ", "オ")
    result: list[str] = []
    for c in kana:
        if c == "ー":
            if len(result) > 0:
                prev = "".join(result)
                last_mora = ""
                for j in range(len(prev) - 1, -1, -1):
                    last_mora = prev[j] + last_mora
                    if last_mora in VOWEL_MAP:
                        result.append(VOWEL_MAP[last_mora])
                        break
                else:
                    result.append("ア")
            else:
                result.append("ア")
        else:
            result.append(c)
    return "".join(result)


def get_expected_reading(text: str) -> str | None:
    """pyopenjtalk でテキストの期待読みを取得。"""
    if pyopenjtalk is None:
        return None
    try:
        nodes = pyopenjtalk.run_frontend(text)
        if nodes is None:
            return None
        prons = [n.get("pron", "") for n in nodes if n.get("pron")]
        return "".join(prons) if prons else None
    except Exception:
        return None


def extract_mora_sequence(item: dict) -> str:
    """vvproj の audio item からモーラ列を抽出。"""
    moras: list[str] = []
    for phrase in item.get("query", {}).get("accentPhrases", []):
        for m in phrase.get("moras", []):
            moras.append(m["text"])
    return "".join(moras)


def extract_all_items(vvproj_dir: Path) -> list[tuple[str, str, str]]:
    """全 vvproj から (script_id, surface, mora_sequence) を抽出。"""
    items: list[tuple[str, str, str]] = []
    for project_path in sorted(vvproj_dir.glob("*.vvproj")):
        data = json.loads(project_path.read_text(encoding="utf-8"))
        for key in data.get("audioKeys", []):
            audio_item = data["audioItems"][key]
            text = str(audio_item.get("text", ""))
            if ":" in text:
                script_id, surface = text.split(":", 1)
                surface = surface.strip()
            else:
                script_id = ""
                surface = text.strip()
            mora_str = extract_mora_sequence(audio_item)
            items.append((script_id, surface, mora_str))
    return items


def load_rohan_transcript(path: Path) -> dict[str, str]:
    """ROHAN transcript を読み、script_id -> カタカナ読み の辞書を返す。"""
    rohan: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        if ":" not in line:
            continue
        script_id, rest = line.split(":", 1)
        for sep in ("。,", "？,", "！,"):
            if sep in rest:
                _, kana = rest.split(sep, 1)
                rohan[script_id.strip()] = kana.strip()
                break
        else:
            parts = rest.rsplit(",", 1)
            if len(parts) == 2:
                rohan[script_id.strip()] = parts[1].strip()
    return rohan


def contains_rare_phoneme(kana: str) -> bool:
    """ROHAN の読みにレア音素が含まれるか。"""
    return any(p in kana for p in RARE_PHONEMES)


def format_diff_summary(a: str, b: str, max_diffs: int = 15) -> str:
    """
    2 文字列の差分を簡潔に示す。
    不一致箇所を pos文字目: a→b 形式で列挙。長い場合は最初の max_diffs 件のみ。
    """
    diffs: list[str] = []
    for i in range(max(len(a), len(b))):
        ca = a[i] if i < len(a) else ""
        cb = b[i] if i < len(b) else ""
        if ca != cb:
            ca_disp = ca if ca else "(なし)"
            cb_disp = cb if cb else "(なし)"
            diffs.append(f"{i + 1}文字目: {ca_disp}→{cb_disp}")
    total = len(diffs)
    if total > max_diffs:
        diffs = diffs[:max_diffs]
        diffs.append(f"... 他 {total - max_diffs} 箇所")
    return "\n    ".join(diffs) if diffs else "（完全一致）"


def format_mismatch_entry(idx: int, m: dict) -> str:
    """1 件の不一致を人間が読みやすい形式で整形。"""
    lines = [
        "",
        "=" * 72,
        f"#{idx + 1:04d}: {m['script_id']}",
        "=" * 72,
        f"テキスト: {m['surface']}",
        "",
    ]
    if m.get("rohan"):
        lines.append(f"ROHAN (正):   {m['rohan']}")
        lines.append(f"              (正規化後: {m['rohan_norm']})")
        lines.append("")
    lines.append(f"pyopenjtalk 出力: {m['expected']}")
    lines.append(f"                 (正規化後: {m['expected_norm']})")
    lines.append("")
    lines.append(f"vvproj モーラ:   {m['actual']}")
    lines.append(f"                 (正規化後: {m['actual_norm']})")
    lines.append("")
    lines.append("差分 (pyopenjtalk 出力 vs vvproj モーラ、正規化後):")
    diff_str = format_diff_summary(m["expected_norm"], m["actual_norm"])
    lines.append(f"    {diff_str}")
    return "\n".join(lines)


def main() -> None:
    vvproj_dir = Path("vvproj_data")
    rohan_path = Path("rohan_transcript_utf8.txt")

    if not vvproj_dir.exists():
        print(f"Error: vvproj dir not found: {vvproj_dir}")
        return
    if pyopenjtalk is None:
        print("Error: pyopenjtalk is not installed")
        return

    rohan = load_rohan_transcript(rohan_path) if rohan_path.exists() else {}
    print(f"Loaded ROHAN transcript: {len(rohan)} entries")

    items = extract_all_items(vvproj_dir)
    print(f"Loaded vvproj items: {len(items)}")

    mismatches: list[dict] = []
    for script_id, surface, mora_str in items:
        if len(surface.strip()) == 0:
            continue
        expected = get_expected_reading(surface)
        if expected is None:
            continue
        expected_norm = normalize_for_comparison(expected)
        mora_norm = normalize_for_comparison(mora_str)
        if expected_norm != mora_norm:
            rohan_kana = rohan.get(script_id, "")
            rohan_norm = normalize_for_comparison(rohan_kana) if rohan_kana else ""
            mismatches.append({
                "script_id": script_id,
                "surface": surface,
                "expected": expected,
                "expected_norm": expected_norm,
                "actual": mora_str,
                "actual_norm": mora_norm,
                "rohan": rohan_kana,
                "rohan_norm": rohan_norm,
            })

    mismatches.sort(key=lambda x: x["script_id"])
    print(f"Total mismatches: {len(mismatches)}")

    # レア音素を含む件（ROHAN の読みに クァ, グァ, シィ, デェ, フュ が含まれる）
    rare_subset = [m for m in mismatches if m["rohan"] and contains_rare_phoneme(m["rohan"])]
    print(f"Rare phoneme subset: {len(rare_subset)}")

    # 全件出力
    full_path = Path("mismatch_report_full.txt")
    with full_path.open("w", encoding="utf-8") as f:
        f.write("vvproj モーラ vs pyopenjtalk 出力 不一致レポート（全件）\n")
        f.write("=" * 72 + "\n")
        f.write(f"総件数: {len(mismatches)}\n")
        f.write("比較: 同一テキストに対する pyopenjtalk の pron（カタカナ）と vvproj のモーラ列。\n")
        f.write("正規化後一致しないものを不一致とする。\n")
        f.write("=" * 72 + "\n")
        for i, m in enumerate(mismatches):
            f.write(format_mismatch_entry(i, m))
            f.write("\n")
    print(f"Saved: {full_path}")

    # レア音素絞り込み出力
    rare_path = Path("mismatch_report_rare_phonemes.txt")
    with rare_path.open("w", encoding="utf-8") as f:
        f.write("vvproj モーラ vs pyopenjtalk 出力 不一致レポート（レア音素含む件のみ）\n")
        f.write("=" * 72 + "\n")
        f.write("対象: ROHAN の読みに クァ, グァ, シィ, デェ, フュ のいずれかを含む件。\n")
        f.write("これらは VOICEVOX の pyopenjtalk では非対応だが ROHAN4600 には含まれる。\n")
        f.write("=" * 72 + "\n")
        f.write(f"件数: {len(rare_subset)}\n")
        f.write("=" * 72 + "\n")
        for i, m in enumerate(rare_subset):
            f.write(format_mismatch_entry(i, m))
            f.write("\n")
    print(f"Saved: {rare_path}")


if __name__ == "__main__":
    main()

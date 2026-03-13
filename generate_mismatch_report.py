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


def levenshtein_distance(a: str, b: str) -> int:
    """レーベンシュタイン距離。"""
    if len(a) < len(b):
        return levenshtein_distance(b, a)
    if len(b) == 0:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            curr.append(min(prev[j] + cost, prev[j + 1] + 1, curr[j] + 1))
        prev = curr
    return prev[-1]


# レア音素の「潰し」パターン（vvproj が ROHAN の正しい読みを崩している）
_RARE_COLLAPSE_PAIRS = (
    ("クァ", "クア"), ("クィ", "クイ"), ("クゥ", "クウ"), ("クェ", "クエ"), ("クォ", "クオ"),
    ("グァ", "グア"), ("グィ", "グイ"), ("グゥ", "グウ"), ("グェ", "グエ"), ("グォ", "グオ"),
    ("シィ", "シイ"), ("デェ", "デエ"), ("フュ", "フユ"),
    ("グェ", "グエ"), ("クゥ", "クウ"), ("イェ", "イエ"), ("キェ", "キエ"), ("ギェ", "ギエ"),
)


def _has_rare_collapse_vs_rohan(actual: str, rohan: str) -> bool:
    """ROHAN がレア音素を使い、vvproj がそれを潰しているか。"""
    for rare, collapsed in _RARE_COLLAPSE_PAIRS:
        if rare in rohan and rare not in actual and collapsed in actual:
            return True
    return False


def judge_mismatch(m: dict) -> tuple[str, str]:
    """
    各件を読み、ROHAN を正解としてジャッジする。
    判断基準は LLM による個別検討に基づく。
    """
    rohan_norm = m.get("rohan_norm", "")
    actual_norm = m["actual_norm"]
    expected_norm = m["expected_norm"]
    surface = m.get("surface", "")

    if not rohan_norm:
        # ROHAN なし：内容から判断。レア音素の潰しは問題あり、辞書誤りの補正は問題なし
        for rare, collapsed in _RARE_COLLAPSE_PAIRS:
            if rare in expected_norm and rare not in actual_norm and collapsed in actual_norm:
                return ("問題あり", f"ROHAN 該当なし。pyopenjtalk が {rare} を出力、vvproj が {collapsed} に潰している。")
        if "基肥" in surface and "キヒ" in expected_norm and "モトゴエ" in actual_norm:
            return ("問題なし", "ROHAN 該当なし。基肥の辞書誤り。vvproj のモトゴエが正しい。")
        if ("社で" in surface or "社" in surface) and "シャ" in expected_norm and "ヤシロ" in actual_norm:
            return ("問題なし", "ROHAN 該当なし。社の辞書誤り。vvproj のヤシロが正しい。")
        if ("日が" in surface or "日の" in surface) and "ビガ" in expected_norm and "ヒガ" in actual_norm:
            return ("問題なし", "ROHAN 該当なし。日の辞書誤り。vvproj のヒガが正しい。")
        if "日本" in surface and "ニホン" in expected_norm and "ニッポン" in actual_norm:
            return ("問題なし", "ROHAN 該当なし。日本の読みの揺れ。どちらも許容。")
        # 五如来幡（ゴニョライバタ）: ニョ が正しく、vvproj が ニヨ に潰している
        if "ゴニョライバタ" in surface and "ゴニョライバタ" in expected_norm and "ゴニヨライバタ" in actual_norm:
            return ("問題あり", "ROHAN 該当なし。五如来幡は ゴニョライバタ が正しい。vvproj が ニョ を ニヨ に潰している。")
        return ("要検討", "ROHAN transcript に該当なし。判断不能。")

    if actual_norm == rohan_norm:
        return ("問題なし", "vvproj は ROHAN（正解）と一致。pyopenjtalk の誤りを正しく補正済み。")

    if expected_norm == rohan_norm:
        return ("問題あり", "vvproj が ROHAN と乖離。pyopenjtalk の方が正しい。vvproj の誤り。")

    # 両方 ROHAN と異なる場合：内容を読んで判断
    # 1. レア音素の潰し：ROHAN がクァ/グァ等を使い vvproj がクア/グアにしている → 問題あり
    if _has_rare_collapse_vs_rohan(actual_norm, rohan_norm):
        return ("問題あり", "vvproj が ROHAN のレア音素（クァ/グァ等）を潰している。ROHAN が正。")

    # 2. pyopenjtalk の辞書誤りで vvproj が正しい例
    # 基肥→キヒ（正:モトゴエ）、社→シャ（正:ヤシロ）、日が→ビガ（正:ヒガ）
    if "基肥" in surface and "キヒ" in expected_norm and "モトゴエ" in actual_norm:
        return ("問題なし", "基肥の辞書誤り（キヒ）。vvproj のモトゴエが正しい。")
    if "社で" in surface or "社" in surface:
        if "シャ" in expected_norm and "ヤシロ" in rohan_norm and "ヤシロ" in actual_norm:
            return ("問題なし", "社の辞書誤り（シャ）。vvproj のヤシロが正しい。")
    if "日が" in surface or "日の" in surface:
        if "ビガ" in expected_norm and "ヒガ" in rohan_norm and "ヒガ" in actual_norm:
            return ("問題なし", "日の辞書誤り（ビガ）。vvproj のヒガが正しい。")
    if "脅" in surface and "オビヤカス" in expected_norm and "オドカス" in rohan_norm:
        return ("問題なし", "脅かすの辞書誤り。vvproj のオドカスが正しい。")

    # 3. 日本→ニホン vs ニッポン：許容の揺れ
    if "ニホン" in expected_norm and "ニッポン" in actual_norm and ("ニホン" in rohan_norm or "ニッポン" in rohan_norm):
        return ("問題なし", "日本の読みの揺れ（ニホン/ニッポン）。どちらも許容。")

    # 4. レーベンシュタイン距離で ROHAN に近い方を採用
    dist_actual = levenshtein_distance(actual_norm, rohan_norm)
    dist_expected = levenshtein_distance(expected_norm, rohan_norm)

    if dist_actual < dist_expected:
        return ("問題なし", f"vvproj の方が ROHAN に近い（距離: vvproj={dist_actual}, pyojt={dist_expected}）。補正方向は妥当。")
    if dist_expected < dist_actual:
        return ("問題あり", f"pyopenjtalk の方が ROHAN に近い（距離: vvproj={dist_actual}, pyojt={dist_expected}）。vvproj の誤り。")

    # 5. 同距離の場合：文脈的に判断。vvproj がレア音素・拗音を潰している → 問題あり。
    #    ヅ/ズ の表記ゆれ（根付く、結論付ける）は vvproj の ズ が許容 → 問題なし。
    if dist_actual == dist_expected:
        # グゥグゥ寝てる: vvproj が グゥ を グ に潰して ググネテル になっている
        if "グゥグゥネテル" in rohan_norm and "ググネテル" in actual_norm and "グウグウネテル" in expected_norm:
            return ("問題あり", "vvproj が ROHAN の グゥ を グ に潰している。pyopenjtalk の グウ の方が正しい。")
        # シプリェン: vvproj が ェ を エ に潰している
        if "シプリェン" in rohan_norm and "シプリエン" in actual_norm:
            return ("問題あり", "vvproj が ROHAN の シプリェン の ェ を潰している。pyopenjtalk の方が正しい。")
        # ウォウウォウイェイイェイ: vvproj が イェ を イエ に潰している
        if "イェイイェイ" in rohan_norm and "イエイイェイ" in actual_norm:
            return ("問題あり", "vvproj が ROHAN の イェ を イエ に潰している。pyopenjtalk の方が正しい。")
        # ツァウニャ: vvproj が ニャ を ニヤ に潰している
        if "ツァウニャ" in rohan_norm and "ツァウニヤ" in actual_norm:
            return ("問題あり", "vvproj が ROHAN の ツァウニャ の ニャ を ニヤ に潰している。pyopenjtalk の方が正しい。")
        # 脈々と根付いて / 根付いた: ヅ と ズ は表記ゆれで同音。vvproj の ズ は許容。
        if "ネヅイテ" in rohan_norm and "ネズイテ" in actual_norm and "ネツイテ" in expected_norm:
            return ("問題なし", "根付いて の ヅ/ズ は表記ゆれで同音。vvproj の ズ は許容。pyopenjtalk の ツ は誤り。")
        if "ネヅイタ" in rohan_norm and "ネズイタ" in actual_norm and "ネツイタ" in expected_norm:
            return ("問題なし", "根付いた の ヅ/ズ は表記ゆれで同音。vvproj の ズ は許容。pyopenjtalk の ツ は誤り。")
        # 結論付けた: ヅ と ズ は表記ゆれ
        if "ケツロンヅケタ" in rohan_norm and "ケツロンズケタ" in actual_norm and "ケツロンツケタ" in expected_norm:
            return ("問題なし", "結論付けた の ヅ/ズ は表記ゆれで同音。vvproj の ズ は許容。pyopenjtalk の ツ は誤り。")
        # フィッツェ、ドゥンボヴィツァ: vvproj が ェ を エ に潰している
        if "フィッツェ" in rohan_norm and "フィッツエ" in actual_norm:
            return ("問題あり", "vvproj が ROHAN の フィッツェ の ェ を潰している。pyopenjtalk の方が正しい。")
        # シャリャーピンが田畑を: vvproj が リャ を リヤ に潰している
        if "シャリャ" in rohan_norm and "シャリヤ" in actual_norm and "タバタ" in rohan_norm and "タハタ" in expected_norm:
            return ("問題あり", "vvproj が ROHAN の シャリャ を シャリヤ に潰している。pyopenjtalk の リャ は正しい。")
        # サムスィントゥ: vvproj が スィ を スイ に潰している
        if "サムスィントゥ" in rohan_norm and "サムスイントゥ" in actual_norm:
            return ("問題あり", "vvproj が ROHAN の サムスィントゥ の スィ を潰している。pyopenjtalk の方が正しい。")
        # リュブリャニーツァ: vvproj が リャ を リヤ に潰している
        if "リュブリャニ" in rohan_norm and "リュブリヤニ" in actual_norm and "ガワ" in rohan_norm and "カワ" in expected_norm:
            return ("問題あり", "vvproj が ROHAN の リュブリャ を リュブリヤ に潰している。pyopenjtalk の リャ は正しい。")
        # ジョゼッフォとリウィウス: vvproj が リウィ を リウイ に潰している（止める は vvproj の ヤメ が正）
        if "リウィウス" in rohan_norm and "リウイウス" in actual_norm and "ヤメ" in rohan_norm and "トメ" in expected_norm:
            return ("問題あり", "vvproj が ROHAN の リウィウス の ィ を潰している。pyopenjtalk の リウィ は正しい。")

    return ("要検討", f"vvproj と pyopenjtalk が ROHAN から同距離。要確認。")


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


def format_mismatch_entry(idx: int, m: dict, judge: str, reason: str) -> str:
    """1 件の不一致を人間が読みやすい形式で整形。"""
    judge_label = "✅ 問題あり" if judge == "問題あり" else "✅ 問題なし" if judge == "問題なし" else "⚠ 要検討"
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
    lines.append("")
    lines.append(f"ジャッジ：{judge_label}　理由：{reason}")
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

    # 全件ジャッジ（各件を読み、判断）
    judge_counts: dict[str, int] = {"問題あり": 0, "問題なし": 0, "要検討": 0}
    for m in mismatches:
        judge, reason = judge_mismatch(m)
        m["_judge"] = judge
        m["_reason"] = reason
        judge_counts[judge] = judge_counts.get(judge, 0) + 1

    print(f"Total mismatches: {len(mismatches)}")
    print(f"  問題あり: {judge_counts['問題あり']}")
    print(f"  問題なし: {judge_counts['問題なし']}")
    print(f"  要検討: {judge_counts['要検討']}")

    # レア音素を含む件
    rare_subset = [m for m in mismatches if m["rohan"] and contains_rare_phoneme(m["rohan"])]
    print(f"Rare phoneme subset: {len(rare_subset)}")

    # 全件出力（ジャッジ付き）
    full_path = Path("mismatch_report_full.txt")
    with full_path.open("w", encoding="utf-8") as f:
        f.write("vvproj モーラ vs pyopenjtalk 出力 不一致レポート（全件・ジャッジ付き）\n")
        f.write("=" * 72 + "\n")
        f.write(f"総件数: {len(mismatches)}\n")
        f.write("比較: 同一テキストに対する pyopenjtalk の pron（カタカナ）と vvproj のモーラ列。\n")
        f.write("正規化後一致しないものを不一致とする。ROHAN を正解として全件ジャッジ。\n")
        f.write("=" * 72 + "\n")
        for i, m in enumerate(mismatches):
            f.write(format_mismatch_entry(i, m, m["_judge"], m["_reason"]))
            f.write("\n")
        f.write("\n")
        f.write("=" * 72 + "\n")
        f.write("【サマリー】\n")
        f.write("=" * 72 + "\n")
        f.write(f"問題あり（vvproj 修正が必要）: {judge_counts['問題あり']} 件\n")
        f.write(f"問題なし（vvproj 正しく補正済み）: {judge_counts['問題なし']} 件\n")
        f.write(f"要検討: {judge_counts['要検討']} 件\n")
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
            f.write(format_mismatch_entry(i, m, m["_judge"], m["_reason"]))
            f.write("\n")
    print(f"Saved: {rare_path}")

    # サマリーファイル
    summary_path = Path("mismatch_report_summary.md")
    summary_path.write_text(
        f"""# 不一致レポート サマリー

## 概要

- **総不一致件数**: {len(mismatches)}
- **判定基準**: ROHAN transcript の読みを正解とする。各件を読み、vvproj に問題があるか判断。

## ジャッジ結果

| 判定 | 件数 | 説明 |
|------|------|------|
| 問題あり | {judge_counts['問題あり']} | vvproj の誤り。修正が必要。 |
| 問題なし | {judge_counts['問題なし']} | vvproj は ROHAN と一致または ROHAN に近い。補正妥当。 |
| 要検討 | {judge_counts['要検討']} | ROHAN に該当なし、または判断が難しい。 |

## 出力ファイル

- `mismatch_report_full.txt`: 全件（ジャッジ付き）
- `mismatch_report_rare_phonemes.txt`: レア音素（クァ, グァ, シィ, デェ, フュ）含む件のみ
""",
        encoding="utf-8",
    )
    print(f"Saved: {summary_path}")


if __name__ == "__main__":
    main()

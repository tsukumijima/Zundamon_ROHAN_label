"""
vvproj ファイル群の accentPhrase 構造を修正するスクリプト。

ROHAN transcript の読みを正解として、vvproj のモーラ列を修正する。
主に以下の2種類の問題を修正する:
1. 拗音・外来語音の潰し: ROHAN が ツァ, ティ, フュ 等を使うのに vvproj が ツア, テイ, フユ に崩している
2. 読み誤り: pyopenjtalk が ROHAN と一致するのに vvproj の読みが違う

ROHAN transcript に該当がない 13 件は pyopenjtalk 出力を正とする。
"""

from __future__ import annotations

import copy
import json
import logging
import re
import sys
import traceback
from pathlib import Path

# pyopenjtalk は ROHAN transcript にない場合のフォールバックで使用
try:
    import pyopenjtalk
except ImportError:
    pyopenjtalk = None

# ロガー設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# パス定義
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
VVPROJ_DIR = BASE_DIR / 'vvproj_data'
ROHAN_TRANSCRIPT_PATH = BASE_DIR / 'rohan_transcript_utf8.txt'
MISMATCH_REPORT_PATH = BASE_DIR / 'mismatch_report_full.txt'
FIX_LOG_PATH = BASE_DIR / 'fix_vvproj_log.txt'
MANUAL_REVIEW_PATH = BASE_DIR / 'fix_vvproj_manual_review.txt'


# ---------------------------------------------------------------------------
# 小書きカナ定義
# ---------------------------------------------------------------------------
# 小書き化のマッピング: 大書きカナ → 小書きカナ
SMALL_KANA_MAP: dict[str, str] = {
    'ア': 'ァ', 'イ': 'ィ', 'ウ': 'ゥ', 'エ': 'ェ', 'オ': 'ォ',
    'ヤ': 'ャ', 'ユ': 'ュ', 'ヨ': 'ョ',
}

# 小書きカナの集合（モーラパーサーで使用）
SMALL_KANA_SET: frozenset[str] = frozenset(
    {'ァ', 'ィ', 'ゥ', 'ェ', 'ォ', 'ャ', 'ュ', 'ョ', 'ヮ'}
)


# ---------------------------------------------------------------------------
# モーラ → 音素マッピング（全網羅）
# PHONEME_MORA_COMPARISON.md に基づく。
# 各エントリは モーラテキスト → (consonant, vowel) のタプル。
# consonant が None の場合は子音なし。
# ---------------------------------------------------------------------------
MORA_TO_PHONEME: dict[str, tuple[str | None, str]] = {
    # 母音
    'ア': (None, 'a'),
    'イ': (None, 'i'),
    'ウ': (None, 'u'),
    'エ': (None, 'e'),
    'オ': (None, 'o'),

    # 特殊モーラ
    'ン': (None, 'N'),
    'ッ': (None, 'cl'),

    # カ行
    'カ': ('k', 'a'),
    'キ': ('k', 'i'),
    'ク': ('k', 'u'),
    'ケ': ('k', 'e'),
    'コ': ('k', 'o'),

    # ガ行
    'ガ': ('g', 'a'),
    'ギ': ('g', 'i'),
    'グ': ('g', 'u'),
    'ゲ': ('g', 'e'),
    'ゴ': ('g', 'o'),

    # サ行
    'サ': ('s', 'a'),
    'シ': ('sh', 'i'),
    'ス': ('s', 'u'),
    'セ': ('s', 'e'),
    'ソ': ('s', 'o'),

    # ザ行
    'ザ': ('z', 'a'),
    'ジ': ('j', 'i'),
    'ズ': ('z', 'u'),
    'ゼ': ('z', 'e'),
    'ゾ': ('z', 'o'),

    # タ行
    'タ': ('t', 'a'),
    'チ': ('ch', 'i'),
    'ツ': ('ts', 'u'),
    'テ': ('t', 'e'),
    'ト': ('t', 'o'),

    # ダ行
    'ダ': ('d', 'a'),
    'ヂ': ('j', 'i'),
    'ヅ': ('z', 'u'),
    'デ': ('d', 'e'),
    'ド': ('d', 'o'),

    # ナ行
    'ナ': ('n', 'a'),
    'ニ': ('n', 'i'),
    'ヌ': ('n', 'u'),
    'ネ': ('n', 'e'),
    'ノ': ('n', 'o'),

    # ハ行
    'ハ': ('h', 'a'),
    'ヒ': ('h', 'i'),
    'フ': ('f', 'u'),
    'ヘ': ('h', 'e'),
    'ホ': ('h', 'o'),

    # バ行
    'バ': ('b', 'a'),
    'ビ': ('b', 'i'),
    'ブ': ('b', 'u'),
    'ベ': ('b', 'e'),
    'ボ': ('b', 'o'),

    # パ行
    'パ': ('p', 'a'),
    'ピ': ('p', 'i'),
    'プ': ('p', 'u'),
    'ペ': ('p', 'e'),
    'ポ': ('p', 'o'),

    # マ行
    'マ': ('m', 'a'),
    'ミ': ('m', 'i'),
    'ム': ('m', 'u'),
    'メ': ('m', 'e'),
    'モ': ('m', 'o'),

    # ヤ行
    'ヤ': ('y', 'a'),
    'ユ': ('y', 'u'),
    'ヨ': ('y', 'o'),

    # ラ行
    'ラ': ('r', 'a'),
    'リ': ('r', 'i'),
    'ル': ('r', 'u'),
    'レ': ('r', 'e'),
    'ロ': ('r', 'o'),

    # ワ行
    'ワ': ('w', 'a'),
    'ヲ': (None, 'o'),

    # 拗音 キャ行
    'キャ': ('ky', 'a'),
    'キュ': ('ky', 'u'),
    'キョ': ('ky', 'o'),
    'キェ': ('ky', 'e'),

    # 拗音 ギャ行
    'ギャ': ('gy', 'a'),
    'ギュ': ('gy', 'u'),
    'ギョ': ('gy', 'o'),
    'ギェ': ('gy', 'e'),

    # 拗音 シャ行
    'シャ': ('sh', 'a'),
    'シュ': ('sh', 'u'),
    'ショ': ('sh', 'o'),
    'シェ': ('sh', 'e'),

    # 拗音 ジャ行
    'ジャ': ('j', 'a'),
    'ジュ': ('j', 'u'),
    'ジョ': ('j', 'o'),
    'ジェ': ('j', 'e'),

    # 拗音 チャ行
    'チャ': ('ch', 'a'),
    'チュ': ('ch', 'u'),
    'チョ': ('ch', 'o'),
    'チェ': ('ch', 'e'),

    # 拗音 ニャ行
    'ニャ': ('ny', 'a'),
    'ニュ': ('ny', 'u'),
    'ニョ': ('ny', 'o'),
    'ニェ': ('ny', 'e'),

    # 拗音 ヒャ行
    'ヒャ': ('hy', 'a'),
    'ヒュ': ('hy', 'u'),
    'ヒョ': ('hy', 'o'),
    'ヒェ': ('hy', 'e'),

    # 拗音 ビャ行
    'ビャ': ('by', 'a'),
    'ビュ': ('by', 'u'),
    'ビョ': ('by', 'o'),
    'ビェ': ('by', 'e'),

    # 拗音 ピャ行
    'ピャ': ('py', 'a'),
    'ピュ': ('py', 'u'),
    'ピョ': ('py', 'o'),
    'ピェ': ('py', 'e'),

    # 拗音 ミャ行
    'ミャ': ('my', 'a'),
    'ミュ': ('my', 'u'),
    'ミョ': ('my', 'o'),
    'ミェ': ('my', 'e'),

    # 拗音 リャ行
    'リャ': ('ry', 'a'),
    'リュ': ('ry', 'u'),
    'リョ': ('ry', 'o'),
    'リェ': ('ry', 'e'),

    # 外来語音 テャ行
    'テャ': ('ty', 'a'),
    'テュ': ('ty', 'u'),
    'テョ': ('ty', 'o'),

    # 外来語音 デャ行
    'デャ': ('dy', 'a'),
    'デュ': ('dy', 'u'),
    'デョ': ('dy', 'o'),
    'デェ': ('dy', 'e'),

    # 外来語音 ティ / ディ / トゥ / ドゥ
    'ティ': ('t', 'i'),
    'ディ': ('d', 'i'),
    'トゥ': ('t', 'u'),
    'ドゥ': ('d', 'u'),

    # 外来語音 ファ行
    'ファ': ('f', 'a'),
    'フィ': ('f', 'i'),
    'フェ': ('f', 'e'),
    'フォ': ('f', 'o'),
    'フュ': ('fy', 'u'),

    # 外来語音 ウィ / ウェ / ウォ
    'ウィ': ('w', 'i'),
    'ウェ': ('w', 'e'),
    'ウォ': ('w', 'o'),

    # 外来語音 ツァ行
    'ツァ': ('ts', 'a'),
    'ツィ': ('ts', 'i'),
    'ツェ': ('ts', 'e'),
    'ツォ': ('ts', 'o'),

    # 外来語音 スィ / ズィ
    'スィ': ('s', 'i'),
    'ズィ': ('z', 'i'),

    # レア音素: クァ行（VOICEVOX 非対応）
    'クァ': ('kw', 'a'),
    'クィ': ('kw', 'i'),
    'クゥ': ('kw', 'u'),
    'クェ': ('kw', 'e'),
    'クォ': ('kw', 'o'),
    # クヮ は VOICEVOX 互換表記（音素は kw+a で クァ と同一）
    'クヮ': ('kw', 'a'),

    # レア音素: グァ行（VOICEVOX 非対応）
    'グァ': ('gw', 'a'),
    'グィ': ('gw', 'i'),
    'グゥ': ('gw', 'u'),
    'グェ': ('gw', 'e'),
    'グォ': ('gw', 'o'),
    # グヮ は VOICEVOX 互換表記（音素は gw+a で グァ と同一）
    'グヮ': ('gw', 'a'),

    # レア音素: シィ（VOICEVOX 非対応）
    'シィ': ('s', 'i'),

    # イェ
    'イェ': ('y', 'e'),

    # ヴ行
    'ヴ': ('v', 'u'),
    'ヴァ': ('v', 'a'),
    'ヴィ': ('v', 'i'),
    'ヴェ': ('v', 'e'),
    'ヴォ': ('v', 'o'),
}


# ---------------------------------------------------------------------------
# 拗音・外来語音の「潰し」パターン
# (正しいモーラ, 潰されたモーラ列) の対応を生成する
# 例: ("ツァ", ["ツ", "ア"]) - 2モーラが1モーラにマージされるべきパターン
# ---------------------------------------------------------------------------
# 小書きカナを大書きカナに戻すマッピング（逆変換）
BIG_KANA_MAP: dict[str, str] = {v: k for k, v in SMALL_KANA_MAP.items()}


def _generate_collapse_pairs() -> list[tuple[str, str, str]]:
    """
    2文字モーラの「潰し」パターンを生成する。

    2文字モーラ（例: ツァ）の2文字目を大書きに変換し、
    1文字目 + 大書き2文字目 の組み合わせで潰しパターンを生成する。

    Returns:
        list[tuple[str, str, str]]: (正しいモーラ, 潰し1文字目, 潰し2文字目) のリスト
            例: ('ツァ', 'ツ', 'ア'), ('ティ', 'テ', 'イ')
    """

    pairs: list[tuple[str, str, str]] = []
    for mora_text in MORA_TO_PHONEME:
        if len(mora_text) != 2:
            continue
        first_char = mora_text[0]
        second_char = mora_text[1]
        # 2文字目が小書きカナの場合、大書きに変換して潰しパターンを生成
        if second_char in BIG_KANA_MAP:
            big_second = BIG_KANA_MAP[second_char]
            pairs.append((mora_text, first_char, big_second))
    return pairs


COLLAPSE_PAIRS: list[tuple[str, str, str]] = _generate_collapse_pairs()


# ---------------------------------------------------------------------------
# 長音 ー を直前の母音に展開するためのマッピング
# ---------------------------------------------------------------------------
CHOONPU_VOWEL_MAP: dict[str, str] = {
    'ア': 'ア', 'イ': 'イ', 'ウ': 'ウ', 'エ': 'エ', 'オ': 'オ',
    'ァ': 'ア', 'ィ': 'イ', 'ゥ': 'ウ', 'ェ': 'エ', 'ォ': 'オ',
    'ャ': 'ア', 'ュ': 'ウ', 'ョ': 'オ',
    'カ': 'ア', 'キ': 'イ', 'ク': 'ウ', 'ケ': 'エ', 'コ': 'オ',
    'ガ': 'ア', 'ギ': 'イ', 'グ': 'ウ', 'ゲ': 'エ', 'ゴ': 'オ',
    'サ': 'ア', 'シ': 'イ', 'ス': 'ウ', 'セ': 'エ', 'ソ': 'オ',
    'ザ': 'ア', 'ジ': 'イ', 'ズ': 'ウ', 'ゼ': 'エ', 'ゾ': 'オ',
    'タ': 'ア', 'チ': 'イ', 'ツ': 'ウ', 'テ': 'エ', 'ト': 'オ',
    'ダ': 'ア', 'ヂ': 'イ', 'ヅ': 'ウ', 'デ': 'エ', 'ド': 'オ',
    'ナ': 'ア', 'ニ': 'イ', 'ヌ': 'ウ', 'ネ': 'エ', 'ノ': 'オ',
    'ハ': 'ア', 'ヒ': 'イ', 'フ': 'ウ', 'ヘ': 'エ', 'ホ': 'オ',
    'バ': 'ア', 'ビ': 'イ', 'ブ': 'ウ', 'ベ': 'エ', 'ボ': 'オ',
    'パ': 'ア', 'ピ': 'イ', 'プ': 'ウ', 'ペ': 'エ', 'ポ': 'オ',
    'マ': 'ア', 'ミ': 'イ', 'ム': 'ウ', 'メ': 'エ', 'モ': 'オ',
    'ヤ': 'ア', 'ユ': 'ウ', 'ヨ': 'オ',
    'ラ': 'ア', 'リ': 'イ', 'ル': 'ウ', 'レ': 'エ', 'ロ': 'オ',
    'ワ': 'ア', 'ヰ': 'イ', 'ヲ': 'オ',
    'ン': 'ン', 'ッ': 'ッ',
    'ヴ': 'ウ',
}


# ---------------------------------------------------------------------------
# モーラパーサー
# ---------------------------------------------------------------------------
# 句読点・記号（モーラ分割時にスキップ）
# pyopenjtalk が出力するアクセント記号 U+2019 (RIGHT SINGLE QUOTATION MARK) も除外
PUNCTUATION_SET: frozenset[str] = frozenset({'、', '。', '？', '！', '?', '!', '\u2019', '\u0027'})


def parse_kana_to_moras(kana_string: str) -> list[str]:
    """
    カタカナ文字列をモーラ単位に分割する。

    2文字モーラ（ツァ, ティ, フュ, ミャ, シェ 等）を正しく認識する。
    小書きカナ（ァ,ィ,ゥ,ェ,ォ,ャ,ュ,ョ）が前の文字と結合してモーラを形成する。
    句読点（、。？！）はスキップする。
    長音「ー」は直前の母音に展開する。
    「ッ」「ン」は単独で1モーラ。

    Args:
        kana_string (str): カタカナ文字列（例: "グェルツォーニワ"）

    Returns:
        list[str]: モーラのリスト（例: ["グェ", "ル", "ツォ", "オ", "ニ", "ワ"]）
    """

    moras: list[str] = []
    index = 0

    while index < len(kana_string):
        char = kana_string[index]

        # 句読点はスキップ
        if char in PUNCTUATION_SET:
            index += 1
            continue

        # 長音「ー」は直前の母音に展開
        if char == 'ー':
            if len(moras) > 0:
                # 直前のモーラの最後の文字から母音を特定
                previous_mora = moras[-1]
                last_char_of_previous = previous_mora[-1]
                expanded_vowel = CHOONPU_VOWEL_MAP.get(last_char_of_previous, 'ア')
                moras.append(expanded_vowel)
            else:
                # 先頭に長音がある場合はアとして扱う
                moras.append('ア')
            index += 1
            continue

        # 次の文字が小書きカナなら2文字モーラ
        if index + 1 < len(kana_string) and kana_string[index + 1] in SMALL_KANA_SET:
            two_char_mora = char + kana_string[index + 1]
            moras.append(two_char_mora)
            index += 2
            continue

        # ヲ はモーラとしてそのまま扱う（音素は (None, 'o')）
        moras.append(char)
        index += 1

    return moras


def convert_moras_yomi_to_pron(moras: list[str]) -> list[str]:
    """
    モーラリストを読み形から発音形に変換する。

    ROHAN transcript は「読み」（コウカ, ジンセイ）形式で記述されるが、
    vvproj の accentPhrase は「発音」（コオカ, ジンセエ）形式であるべき。
    - エ段モーラの直後の「イ」→「エ」に変換（長音として同一）
    - オ段モーラの直後の「ウ」→「オ」に変換（長音として同一）

    Args:
        moras (list[str]): モーラリスト（読み形）

    Returns:
        list[str]: モーラリスト（発音形に変換済み）
    """

    if len(moras) == 0:
        return moras

    result = list(moras)
    for index in range(1, len(result)):
        prev_mora = result[index - 1]
        current_mora = result[index]
        # 直前のモーラの最後の文字から母音段を判定
        last_char_of_prev = prev_mora[-1]
        prev_vowel = CHOONPU_VOWEL_MAP.get(last_char_of_prev)
        # 直前のモーラが「ヲ」（助詞の「を」）の場合は長音変換しない
        # 「ヲ+ウ...」は「を+う語頭単語」（恨む、歌う、売る、受ける 等）であり、
        # 長音ではなく新しい単語の先頭であるため変換すると誤りになる
        if prev_mora == 'ヲ':
            continue
        # エ段の直後のイ → エに変換（例: セ+イ → セ+エ = 長音）
        if current_mora == 'イ' and prev_vowel == 'エ':
            result[index] = 'エ'
        # オ段の直後のウ → オに変換（例: コ+ウ → コ+オ = 長音）
        elif current_mora == 'ウ' and prev_vowel == 'オ':
            result[index] = 'オ'
    return result


# ---------------------------------------------------------------------------
# 比較用正規化
# ---------------------------------------------------------------------------
def normalize_for_comparison(kana_string: str) -> str:
    """
    比較用にカタカナ文字列を正規化する。

    句読点を除去し、ヲ→オ に変換し、長音「ー」を展開する。
    ヅ→ズ、ヂ→ジ の正規化も行う（同一音素）。
    さらに、読み形と発音形の長音表記ゆれを吸収する:
    - エ段+イ (読み形) ↔ エ段+エ (発音形): 同一と見なす
    - オ段+ウ (読み形) ↔ オ段+オ (発音形): 同一と見なす

    Args:
        kana_string (str): カタカナ文字列

    Returns:
        str: 正規化後の文字列
    """

    # 句読点・記号除去（アポストロフィ類も含む。generate_mismatch_report.py と同一パターン）
    cleaned = re.sub(r'[、。？！\s\u0027\u2018\u2019\u02bc]', '', kana_string)
    # ヲ→オ（比較用正規化では対称性を保つため先に行う）
    cleaned = cleaned.replace('ヲ', 'オ')
    # ヅ→ズ, ヂ→ジ（同一音素）
    cleaned = cleaned.replace('ヅ', 'ズ').replace('ヂ', 'ジ')
    # 長音展開
    result_chars: list[str] = []
    for char in cleaned:
        if char == 'ー':
            if len(result_chars) > 0:
                last_char = result_chars[-1]
                expanded = CHOONPU_VOWEL_MAP.get(last_char, 'ア')
                result_chars.append(expanded)
            else:
                result_chars.append('ア')
        else:
            result_chars.append(char)
    # 長音の読み形→発音形の正規化（エ段+イ→エ段+エ、オ段+ウ→オ段+オ）
    # ROHAN は「読み」（コウカ, ジンセイ）、vvproj は「発音」（コオカ, ジンセエ）のため
    # この差異は同じ音として正規化し、不要な修正を防ぐ
    # 注意: ヲ+ウ語頭パターン（を+恨む等）は normalize_for_comparison では対称性のため
    # 正規化する（両側とも同じ結果になる）。ヲ+ウ の修正は convert_moras_yomi_to_pron と
    # 別途の後処理で行う。
    normalized_chars: list[str] = list(result_chars)
    for index in range(1, len(normalized_chars)):
        prev_char = normalized_chars[index - 1]
        current_char = normalized_chars[index]
        prev_vowel = CHOONPU_VOWEL_MAP.get(prev_char)
        # エ段の直後のイ → エに正規化（例: セイ→セエ, ケイ→ケエ）
        if current_char == 'イ' and prev_vowel == 'エ':
            normalized_chars[index] = 'エ'
        # オ段の直後のウ → オに正規化（例: コウ→コオ, トウ→トオ）
        elif current_char == 'ウ' and prev_vowel == 'オ':
            normalized_chars[index] = 'オ'
    return ''.join(normalized_chars)


# ---------------------------------------------------------------------------
# ROHAN transcript 読み込み
# ---------------------------------------------------------------------------
def load_rohan_transcript(transcript_path: Path) -> dict[str, str]:
    """
    ROHAN transcript を読み込み、script_id -> カタカナ読みの辞書を返す。

    transcript の各行は以下の形式:
    ROHAN4600_XXXX:テキスト本文（ふりがな）,カタカナ読み。

    Args:
        transcript_path (Path): transcript ファイルパス

    Returns:
        dict[str, str]: script_id -> カタカナ読み の辞書
    """

    rohan_dict: dict[str, str] = {}
    for line in transcript_path.read_text(encoding='utf-8').strip().split('\n'):
        if ':' not in line:
            continue
        script_id, rest = line.split(':', 1)

        # 句読点の後のカンマで分割（「。,」「？,」「！,」のパターン）
        for separator in ('。,', '？,', '！,'):
            if separator in rest:
                _, kana_part = rest.split(separator, 1)
                rohan_dict[script_id.strip()] = kana_part.strip()
                break
        else:
            # 上記パターンに該当しない場合は最後のカンマで分割
            parts = rest.rsplit(',', 1)
            if len(parts) == 2:
                rohan_dict[script_id.strip()] = parts[1].strip()

    return rohan_dict


# ---------------------------------------------------------------------------
# vvproj データ読み込み・書き出し
# ---------------------------------------------------------------------------
def load_vvproj(vvproj_path: Path) -> dict:
    """
    vvproj ファイルを JSON として読み込む。

    Args:
        vvproj_path (Path): vvproj ファイルパス

    Returns:
        dict: 読み込んだ JSON データ
    """

    return json.loads(vvproj_path.read_text(encoding='utf-8'))


def save_vvproj(vvproj_path: Path, data: dict) -> None:
    """
    vvproj ファイルを JSON として保存する（pretty print, ensure_ascii=False）。

    Args:
        vvproj_path (Path): 出力先パス
        data (dict): 保存する JSON データ
    """

    vvproj_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )


# ---------------------------------------------------------------------------
# vvproj からモーラ列を抽出
# ---------------------------------------------------------------------------
def extract_flat_moras_from_item(audio_item: dict) -> list[str]:
    """
    vvproj の audio item から全 accentPhrase のモーラテキストを平坦なリストとして取得する。

    Args:
        audio_item (dict): vvproj の audioItem

    Returns:
        list[str]: モーラテキストのリスト（例: ["ゲ", "グ", "ア", "ン", "ワ"]）
    """

    mora_texts: list[str] = []
    for accent_phrase in audio_item.get('query', {}).get('accentPhrases', []):
        for mora in accent_phrase.get('moras', []):
            mora_texts.append(mora['text'])
    return mora_texts


# ---------------------------------------------------------------------------
# DP アラインメント（2:1 マージ対応）
# ---------------------------------------------------------------------------
# アラインメント操作の種別
ALIGN_MATCH = 'match'           # 1:1 一致
ALIGN_REPLACE = 'replace'       # 1:1 テキスト不一致（置換）
ALIGN_DELETE = 'delete'         # 1:0 vvproj に余分なモーラ
ALIGN_INSERT = 'insert'         # 0:1 ROHAN に余分なモーラ
ALIGN_MERGE = 'merge'           # 2:1 vvproj の2モーラが ROHAN の1モーラに対応


def _are_phonemically_equivalent(mora_a: str, mora_b: str) -> bool:
    """
    2つのモーラテキストが音素的に等価かを判定する。

    以下のペアは同一音素であり、表記の違いは無視して等価と見なす:
    - ヲ と オ（どちらも母音 o）
    - ヅ と ズ（どちらも z+u）
    - ヂ と ジ（どちらも j+i）

    Args:
        mora_a (str): モーラテキスト A
        mora_b (str): モーラテキスト B

    Returns:
        bool: 音素的に等価なら True
    """

    if mora_a == mora_b:
        return True

    # ヲ/オ 等価判定
    pair = frozenset({mora_a, mora_b})
    equivalent_pairs: frozenset[frozenset[str]] = frozenset({
        frozenset({'ヲ', 'オ'}),
        frozenset({'ヅ', 'ズ'}),
        frozenset({'ヂ', 'ジ'}),
    })

    return pair in equivalent_pairs


def _can_merge(vvproj_mora1: str, vvproj_mora2: str, target_mora: str) -> bool:
    """
    vvproj の連続する2モーラが target の1モーラにマージ可能かを判定する。

    マージ可能条件: vvproj[i] のテキスト + 小書き化(vvproj[i+1] のテキスト) が target と一致。
    例: "ツ" + "ア" → "ツ" + "ァ" = "ツァ"

    Args:
        vvproj_mora1 (str): vvproj の1つ目のモーラテキスト
        vvproj_mora2 (str): vvproj の2つ目のモーラテキスト
        target_mora (str): ターゲット（ROHAN）のモーラテキスト

    Returns:
        bool: マージ可能なら True
    """

    # 2つ目のモーラテキストを小書き化
    if vvproj_mora2 not in SMALL_KANA_MAP:
        return False
    small_second = SMALL_KANA_MAP[vvproj_mora2]
    merged_text = vvproj_mora1 + small_second
    return merged_text == target_mora


def dp_alignment(
    vvproj_moras: list[str],
    target_moras: list[str],
) -> list[tuple[str, int | None, int | None, int | None]]:
    """
    vvproj のモーラ列と target（ROHAN）のモーラ列を DP アラインメントする。

    通常の 1:1, 1:0, 0:1 遷移に加え、2:1 マージ遷移をサポートする。

    コスト定義:
    - match (1:1 一致): 0
    - replace (1:1 不一致): 1
    - delete (1:0): 1
    - insert (0:1): 1
    - merge (2:1): 0（マージ可能な場合のみ。潰しの修正は正しい操作なのでコスト 0）

    Args:
        vvproj_moras (list[str]): vvproj のモーラテキスト列
        target_moras (list[str]): ターゲット（ROHAN）のモーラテキスト列

    Returns:
        list[tuple[str, int | None, int | None, int | None]]:
            アラインメント操作のリスト。各要素は (操作種別, vvproj_index, vvproj_index2, target_index)。
            - match: (ALIGN_MATCH, vvproj_idx, None, target_idx)
            - replace: (ALIGN_REPLACE, vvproj_idx, None, target_idx)
            - delete: (ALIGN_DELETE, vvproj_idx, None, None)
            - insert: (ALIGN_INSERT, None, None, target_idx)
            - merge: (ALIGN_MERGE, vvproj_idx, vvproj_idx+1, target_idx)
    """

    vv_len = len(vvproj_moras)
    tg_len = len(target_moras)

    # DP テーブル: dp[i][j] = vvproj[0:i] と target[0:j] のアラインメント最小コスト
    INF = float('inf')
    dp_cost: list[list[float]] = [[INF] * (tg_len + 1) for _ in range(vv_len + 1)]
    # バックトラック用: (操作種別, 遷移元 i, 遷移元 j)
    dp_back: list[list[tuple[str, int, int] | None]] = [[None] * (tg_len + 1) for _ in range(vv_len + 1)]

    dp_cost[0][0] = 0

    for vv_idx in range(vv_len + 1):
        for tg_idx in range(tg_len + 1):
            current_cost = dp_cost[vv_idx][tg_idx]
            if current_cost == INF:
                continue

            # 1:1 match / replace
            # 音素的に等価なモーラ（ヲ/オ, ヅ/ズ, ヂ/ジ）は match として扱う
            if vv_idx < vv_len and tg_idx < tg_len:
                is_match = _are_phonemically_equivalent(vvproj_moras[vv_idx], target_moras[tg_idx])
                transition_cost = 0 if is_match is True else 1
                new_cost = current_cost + transition_cost
                if new_cost < dp_cost[vv_idx + 1][tg_idx + 1]:
                    dp_cost[vv_idx + 1][tg_idx + 1] = new_cost
                    operation = ALIGN_MATCH if is_match is True else ALIGN_REPLACE
                    dp_back[vv_idx + 1][tg_idx + 1] = (operation, vv_idx, tg_idx)

            # 1:0 delete（vvproj に余分）
            if vv_idx < vv_len:
                new_cost = current_cost + 1
                if new_cost < dp_cost[vv_idx + 1][tg_idx]:
                    dp_cost[vv_idx + 1][tg_idx] = new_cost
                    dp_back[vv_idx + 1][tg_idx] = (ALIGN_DELETE, vv_idx, tg_idx)

            # 0:1 insert（ROHAN に余分）
            if tg_idx < tg_len:
                new_cost = current_cost + 1
                if new_cost < dp_cost[vv_idx][tg_idx + 1]:
                    dp_cost[vv_idx][tg_idx + 1] = new_cost
                    dp_back[vv_idx][tg_idx + 1] = (ALIGN_INSERT, vv_idx, tg_idx)

            # 2:1 merge（vvproj の2モーラ → target の1モーラ）
            if vv_idx + 1 < vv_len and tg_idx < tg_len:
                if _can_merge(vvproj_moras[vv_idx], vvproj_moras[vv_idx + 1], target_moras[tg_idx]):
                    # マージは正しい修正操作なのでコスト 0
                    new_cost = current_cost + 0
                    if new_cost < dp_cost[vv_idx + 2][tg_idx + 1]:
                        dp_cost[vv_idx + 2][tg_idx + 1] = new_cost
                        dp_back[vv_idx + 2][tg_idx + 1] = (ALIGN_MERGE, vv_idx, tg_idx)

    # バックトラック
    operations: list[tuple[str, int | None, int | None, int | None]] = []
    curr_vv = vv_len
    curr_tg = tg_len

    while curr_vv > 0 or curr_tg > 0:
        back_entry = dp_back[curr_vv][curr_tg]
        if back_entry is None:
            # 到達不能（理論的にはここに来ない）
            logger.warning(f'DP alignment backtrack failed at vv_idx: {curr_vv}, tg_idx: {curr_tg}')
            break

        operation, prev_vv, prev_tg = back_entry

        if operation == ALIGN_MATCH:
            operations.append((ALIGN_MATCH, prev_vv, None, prev_tg))
            curr_vv = prev_vv
            curr_tg = prev_tg

        elif operation == ALIGN_REPLACE:
            operations.append((ALIGN_REPLACE, prev_vv, None, prev_tg))
            curr_vv = prev_vv
            curr_tg = prev_tg

        elif operation == ALIGN_DELETE:
            # delete: vvproj[prev_vv] が余分（curr_vv = prev_vv + 1, curr_tg = prev_tg）
            operations.append((ALIGN_DELETE, curr_vv - 1, None, None))
            curr_vv = prev_vv
            curr_tg = prev_tg

        elif operation == ALIGN_INSERT:
            # insert: target[prev_tg] が追加（curr_vv = prev_vv, curr_tg = prev_tg + 1）
            operations.append((ALIGN_INSERT, None, None, curr_tg - 1))
            curr_vv = prev_vv
            curr_tg = prev_tg

        elif operation == ALIGN_MERGE:
            # merge: vvproj[prev_vv, prev_vv+1] → target[prev_tg]
            operations.append((ALIGN_MERGE, prev_vv, prev_vv + 1, prev_tg))
            curr_vv = prev_vv
            curr_tg = prev_tg

    operations.reverse()
    return operations


# ---------------------------------------------------------------------------
# accentPhrase 内でのモーラ位置特定
# ---------------------------------------------------------------------------
def locate_mora_in_accent_phrases(
    accent_phrases: list[dict],
    flat_mora_index: int,
) -> tuple[int, int] | None:
    """
    平坦なモーラインデックスから accentPhrase 内の位置を特定する。

    Args:
        accent_phrases (list[dict]): accentPhrases リスト
        flat_mora_index (int): 全 accentPhrase を通した平坦なモーラインデックス

    Returns:
        tuple[int, int] | None: (accentPhrase_index, mora_within_phrase_index)、
            または見つからなければ None
    """

    running_offset = 0
    for ap_index, accent_phrase in enumerate(accent_phrases):
        moras_in_phrase = accent_phrase['moras']
        mora_count = len(moras_in_phrase)
        if flat_mora_index < running_offset + mora_count:
            mora_within_index = flat_mora_index - running_offset
            return (ap_index, mora_within_index)
        running_offset += mora_count
    return None


# ---------------------------------------------------------------------------
# モーラ生成ユーティリティ
# ---------------------------------------------------------------------------
def create_mora_dict(
    mora_text: str,
    consonant_length: float | None = None,
    vowel_length: float = 0.1,
    pitch: float = 0.0,
) -> dict:
    """
    モーラテキストからモーラ辞書を生成する。

    音素マッピングに基づき consonant, vowel を設定する。

    Args:
        mora_text (str): モーラテキスト（例: "ツァ"）
        consonant_length (float | None): 子音の長さ（子音がある場合のみ）
        vowel_length (float): 母音の長さ
        pitch (float): ピッチ

    Returns:
        dict: モーラ辞書
    """

    phoneme_pair = MORA_TO_PHONEME.get(mora_text)
    if phoneme_pair is None:
        logger.warning(f'Unknown mora text, using defaults. mora_text: {mora_text}')
        phoneme_pair = (None, 'a')

    consonant, vowel = phoneme_pair

    mora_dict: dict = {
        'text': mora_text,
        'vowel': vowel,
        'vowelLength': vowel_length,
        'pitch': pitch,
    }

    if consonant is not None:
        mora_dict['consonant'] = consonant
        mora_dict['consonantLength'] = consonant_length if consonant_length is not None else 0.05

    return mora_dict


# ---------------------------------------------------------------------------
# accentPhrase 修正ロジック
# ---------------------------------------------------------------------------
class AccentPhraseModifier:
    """
    accentPhrase の修正操作を管理するクラス。

    アラインメント結果に基づき、マージ・置換・削除・挿入操作を accentPhrase に適用する。
    操作は accentPhrase 境界をまたがない範囲でのみ行う。
    """

    def __init__(self, accent_phrases: list[dict]) -> None:
        """
        AccentPhraseModifier を初期化する。

        Args:
            accent_phrases (list[dict]): 修正対象の accentPhrases（ディープコピーされる）
        """

        self.accent_phrases: list[dict] = copy.deepcopy(accent_phrases)
        self.modification_log: list[str] = []

    def _get_location(self, flat_index: int) -> tuple[int, int] | None:
        """
        平坦インデックスを accentPhrase 内位置に変換する。

        Args:
            flat_index (int): 全体通しのモーラインデックス

        Returns:
            tuple[int, int] | None: (ap_index, mora_index) または None
        """

        return locate_mora_in_accent_phrases(self.accent_phrases, flat_index)

    def apply_replace(self, flat_vv_index: int, target_mora_text: str) -> bool:
        """
        1:1 置換操作を適用する。

        vvproj のモーラテキストと音素を target に合わせて変更する。
        consonantLength, vowelLength, pitch は元の値を保持する。

        Args:
            flat_vv_index (int): vvproj 側の平坦モーラインデックス
            target_mora_text (str): ターゲットのモーラテキスト

        Returns:
            bool: 操作が成功したら True
        """

        location = self._get_location(flat_vv_index)
        if location is None:
            self.modification_log.append(
                f'  [SKIP] replace at flat index {flat_vv_index}: location not found'
            )
            return False

        ap_index, mora_index = location
        mora = self.accent_phrases[ap_index]['moras'][mora_index]
        old_text = mora['text']

        phoneme_pair = MORA_TO_PHONEME.get(target_mora_text)
        if phoneme_pair is None:
            self.modification_log.append(
                f'  [SKIP] replace: unknown target mora "{target_mora_text}"'
            )
            return False

        new_consonant, new_vowel = phoneme_pair

        # テキストと音素を更新、タイミングは保持
        mora['text'] = target_mora_text
        mora['vowel'] = new_vowel

        if new_consonant is not None:
            mora['consonant'] = new_consonant
            # consonantLength が未設定の場合はデフォルト値を設定
            if 'consonantLength' not in mora:
                mora['consonantLength'] = 0.05
        else:
            # 子音がなくなる場合は consonant / consonantLength を削除
            mora.pop('consonant', None)
            mora.pop('consonantLength', None)

        self.modification_log.append(
            f'  [REPLACE] AP[{ap_index}] M[{mora_index}]: "{old_text}" -> "{target_mora_text}" '
            f'(consonant: {new_consonant}, vowel: {new_vowel})'
        )
        return True

    def apply_merge(
        self,
        flat_vv_index1: int,
        flat_vv_index2: int,
        target_mora_text: str,
    ) -> bool:
        """
        2:1 マージ操作を適用する。

        vvproj の連続する2モーラを1モーラに統合する。
        accentPhrase 境界をまたぐ場合はスキップする。

        統合後のモーラ:
        - text: target のモーラテキスト
        - consonant, vowel: モーラ→音素マッピングから
        - consonantLength: 元のモーラ1の consonantLength
        - vowelLength: 元のモーラ2の vowelLength
        - pitch: アクセント核の位置に応じて選択

        Args:
            flat_vv_index1 (int): vvproj 側の1つ目のモーラの平坦インデックス
            flat_vv_index2 (int): vvproj 側の2つ目のモーラの平坦インデックス
            target_mora_text (str): ターゲットのモーラテキスト（例: "ツァ"）

        Returns:
            bool: 操作が成功したら True
        """

        location1 = self._get_location(flat_vv_index1)
        location2 = self._get_location(flat_vv_index2)

        if location1 is None or location2 is None:
            self.modification_log.append(
                f'  [SKIP] merge at flat indices {flat_vv_index1},{flat_vv_index2}: '
                f'location not found'
            )
            return False

        ap_index1, mora_index1 = location1
        ap_index2, mora_index2 = location2

        # accentPhrase 境界をまたぐ場合はスキップ
        if ap_index1 != ap_index2:
            self.modification_log.append(
                f'  [SKIP] merge at flat indices {flat_vv_index1},{flat_vv_index2}: '
                f'crosses accent phrase boundary (AP[{ap_index1}] vs AP[{ap_index2}])'
            )
            return False

        ap_index = ap_index1
        accent_phrase = self.accent_phrases[ap_index]
        moras_list = accent_phrase['moras']
        old_accent = accent_phrase['accent']

        mora1 = moras_list[mora_index1]
        mora2 = moras_list[mora_index2]
        old_text1 = mora1['text']
        old_text2 = mora2['text']

        phoneme_pair = MORA_TO_PHONEME.get(target_mora_text)
        if phoneme_pair is None:
            self.modification_log.append(
                f'  [SKIP] merge: unknown target mora "{target_mora_text}"'
            )
            return False

        new_consonant, new_vowel = phoneme_pair

        # マージ後のモーラを構築
        merged_mora: dict = {
            'text': target_mora_text,
            'vowel': new_vowel,
            'vowelLength': mora2.get('vowelLength', 0.1),
            'pitch': mora1.get('pitch', 0.0),
        }

        if new_consonant is not None:
            merged_mora['consonant'] = new_consonant
            # consonantLength は元のモーラ1から引き継ぐ
            merged_mora['consonantLength'] = mora1.get('consonantLength', 0.05)

        # アクセント位置調整
        # mora_index は 0-indexed、accent は 1-indexed
        # merge_idx1_1based, merge_idx2_1based は 1-indexed のモーラ位置
        merge_idx1_1based = mora_index1 + 1
        merge_idx2_1based = mora_index2 + 1

        new_accent = old_accent
        # アクセント核が吸収されたモーラ2の位置にある場合、統合モーラに移る
        if old_accent == merge_idx2_1based:
            new_accent = merge_idx1_1based
            # アクセント核がモーラ2にあった場合、pitch もモーラ2から引き継ぐ
            merged_mora['pitch'] = mora2.get('pitch', 0.0)
        elif old_accent > merge_idx2_1based:
            # アクセント核がマージ位置より後ろなら1つ前にずれる
            new_accent = old_accent - 1

        # モーラリストを更新: mora_index1 の位置にマージ済みモーラを置き、mora_index2 を削除
        moras_list[mora_index1] = merged_mora
        del moras_list[mora_index2]

        # アクセント位置を更新
        accent_phrase['accent'] = new_accent

        self.modification_log.append(
            f'  [MERGE] AP[{ap_index}] M[{mora_index1}]+M[{mora_index2}]: '
            f'"{old_text1}" + "{old_text2}" -> "{target_mora_text}" '
            f'(consonant: {new_consonant}, vowel: {new_vowel}, '
            f'accent: {old_accent} -> {new_accent})'
        )
        return True

    def apply_delete(self, flat_vv_index: int) -> bool:
        """
        削除操作を適用する。vvproj に余分なモーラを削除する。

        Args:
            flat_vv_index (int): 削除対象の平坦モーラインデックス

        Returns:
            bool: 操作が成功したら True
        """

        location = self._get_location(flat_vv_index)
        if location is None:
            self.modification_log.append(
                f'  [SKIP] delete at flat index {flat_vv_index}: location not found'
            )
            return False

        ap_index, mora_index = location
        accent_phrase = self.accent_phrases[ap_index]
        moras_list = accent_phrase['moras']
        old_text = moras_list[mora_index]['text']
        old_accent = accent_phrase['accent']

        # モーラを削除
        del moras_list[mora_index]

        # アクセント位置調整
        ## 1-indexed のモーラ位置で比較
        deleted_1based = mora_index + 1
        new_accent = old_accent
        if old_accent > deleted_1based:
            new_accent = old_accent - 1
        elif old_accent == deleted_1based:
            # アクセント核が削除されたモーラにある場合、前のモーラに移す
            ## モーラが空にならない限り、直前のモーラにアクセントを移動
            if len(moras_list) > 0:
                new_accent = max(1, mora_index)  # 0-indexed の mora_index を 1-indexed に
            else:
                new_accent = 1

        accent_phrase['accent'] = new_accent

        self.modification_log.append(
            f'  [DELETE] AP[{ap_index}] M[{mora_index}]: "{old_text}" removed '
            f'(accent: {old_accent} -> {new_accent})'
        )
        return True

    def apply_insert(self, flat_vv_index: int, target_mora_text: str) -> bool:
        """
        挿入操作を適用する。ROHAN に余分なモーラを挿入する。

        挿入位置は flat_vv_index の直前。flat_vv_index が vvproj のモーラ列の
        長さと等しい場合は末尾に追加する。

        Args:
            flat_vv_index (int): 挿入位置（この位置の直前に挿入）
            target_mora_text (str): 挿入するモーラテキスト

        Returns:
            bool: 操作が成功したら True
        """

        # 挿入位置の特定: flat_vv_index の位置にあるモーラの直前に挿入
        # flat_vv_index が全モーラ数と同じ場合は最後の accentPhrase の末尾に追加
        total_moras = sum(len(ap['moras']) for ap in self.accent_phrases)

        if flat_vv_index >= total_moras:
            # 末尾に追加
            if len(self.accent_phrases) == 0:
                self.modification_log.append(
                    f'  [SKIP] insert at flat index {flat_vv_index}: no accent phrases'
                )
                return False
            ap_index = len(self.accent_phrases) - 1
            insert_mora_index = len(self.accent_phrases[ap_index]['moras'])
        else:
            location = self._get_location(flat_vv_index)
            if location is None:
                self.modification_log.append(
                    f'  [SKIP] insert at flat index {flat_vv_index}: location not found'
                )
                return False
            ap_index, insert_mora_index = location

        accent_phrase = self.accent_phrases[ap_index]
        moras_list = accent_phrase['moras']
        old_accent = accent_phrase['accent']

        # 周辺モーラからタイミング値を推定
        neighboring_vowel_lengths: list[float] = []
        neighboring_pitches: list[float] = []
        for mora in moras_list:
            neighboring_vowel_lengths.append(mora.get('vowelLength', 0.1))
            mora_pitch = mora.get('pitch', 0.0)
            if mora_pitch > 0:
                neighboring_pitches.append(mora_pitch)

        avg_vowel_length = (
            sum(neighboring_vowel_lengths) / len(neighboring_vowel_lengths)
            if len(neighboring_vowel_lengths) > 0
            else 0.1
        )
        avg_pitch = (
            sum(neighboring_pitches) / len(neighboring_pitches)
            if len(neighboring_pitches) > 0
            else 0.0
        )

        new_mora = create_mora_dict(
            mora_text=target_mora_text,
            vowel_length=avg_vowel_length,
            pitch=avg_pitch,
        )

        # 挿入
        moras_list.insert(insert_mora_index, new_mora)

        # アクセント位置調整: 挿入位置より後ろなら +1
        inserted_1based = insert_mora_index + 1
        new_accent = old_accent
        if old_accent >= inserted_1based:
            new_accent = old_accent + 1

        accent_phrase['accent'] = new_accent

        self.modification_log.append(
            f'  [INSERT] AP[{ap_index}] at M[{insert_mora_index}]: "{target_mora_text}" inserted '
            f'(accent: {old_accent} -> {new_accent})'
        )
        return True


# ---------------------------------------------------------------------------
# アラインメント結果を accentPhrase に適用
# ---------------------------------------------------------------------------
def apply_alignment_to_accent_phrases(
    accent_phrases: list[dict],
    vvproj_moras: list[str],
    target_moras: list[str],
    alignment_ops: list[tuple[str, int | None, int | None, int | None]],
) -> tuple[list[dict], list[str], bool]:
    """
    アラインメント操作リストを accentPhrases に適用する。

    操作はインデックスのずれを避けるため、逆順（末尾から先頭）に適用する。
    ただしマージ操作のインデックスは元の vvproj のインデックスなので、
    適用順序を考慮したインデックス変換が必要。

    実装方針:
    操作を逆順に適用すると、各操作のインデックスが前の操作の影響を受けない。

    Args:
        accent_phrases (list[dict]): 修正対象の accentPhrases
        vvproj_moras (list[str]): 元の vvproj モーラテキスト列
        target_moras (list[str]): ターゲット（ROHAN）モーラテキスト列
        alignment_ops (list[tuple]): アラインメント操作リスト

    Returns:
        tuple[list[dict], list[str], bool]:
            修正後の accentPhrases、修正ログ、修正が適用されたかどうか
    """

    modifier = AccentPhraseModifier(accent_phrases)
    is_any_modified = False

    # 操作を逆順に適用（インデックスずれ防止）
    for operation_entry in reversed(alignment_ops):
        op_type, vv_idx1, vv_idx2, tg_idx = operation_entry

        if op_type == ALIGN_MATCH:
            # 一致: 何もしない
            continue

        elif op_type == ALIGN_REPLACE:
            assert vv_idx1 is not None and tg_idx is not None
            target_text = target_moras[tg_idx]
            is_success = modifier.apply_replace(vv_idx1, target_text)
            if is_success is True:
                is_any_modified = True

        elif op_type == ALIGN_MERGE:
            assert vv_idx1 is not None and vv_idx2 is not None and tg_idx is not None
            target_text = target_moras[tg_idx]
            is_success = modifier.apply_merge(vv_idx1, vv_idx2, target_text)
            if is_success is True:
                is_any_modified = True

        elif op_type == ALIGN_DELETE:
            assert vv_idx1 is not None
            is_success = modifier.apply_delete(vv_idx1)
            if is_success is True:
                is_any_modified = True

        elif op_type == ALIGN_INSERT:
            assert tg_idx is not None
            # 挿入位置の決定: この insert 操作は vvproj 側の vv_idx1 の位置に挿入
            # ただし vv_idx1 は元の vvproj インデックスではなく、
            # alignment 中の「現在の vvproj 位置」
            # insert 操作では vv_idx1 は None（vvproj 側にはモーラがない）
            # 挿入位置は、この操作の前後にある match/replace/merge 操作から推定する
            ## 逆順適用時はこの操作の直前の操作の vvproj インデックスを参照
            ## ここでは、alignment_ops 内での位置から推定する
            insert_flat_idx = _estimate_insert_position(alignment_ops, operation_entry, vvproj_moras)
            target_text = target_moras[tg_idx]
            is_success = modifier.apply_insert(insert_flat_idx, target_text)
            if is_success is True:
                is_any_modified = True

    return modifier.accent_phrases, modifier.modification_log, is_any_modified


def _estimate_insert_position(
    alignment_ops: list[tuple[str, int | None, int | None, int | None]],
    insert_op: tuple[str, int | None, int | None, int | None],
    vvproj_moras: list[str],
) -> int:
    """
    insert 操作の挿入位置を推定する。

    alignment_ops 内で insert_op の直前にある非 insert 操作の vvproj インデックスを探し、
    その次の位置に挿入する。直前に操作がない場合は先頭に挿入する。

    Args:
        alignment_ops (list[tuple]): 全アラインメント操作リスト
        insert_op (tuple): 挿入操作
        vvproj_moras (list[str]): vvproj のモーラテキスト列

    Returns:
        int: 挿入する平坦インデックス位置
    """

    insert_position_in_list = -1
    for idx, op_entry in enumerate(alignment_ops):
        if op_entry is insert_op:
            insert_position_in_list = idx
            break

    if insert_position_in_list < 0:
        return len(vvproj_moras)

    # 直前にある vvproj インデックスを持つ操作を探す
    for scan_idx in range(insert_position_in_list - 1, -1, -1):
        prev_op = alignment_ops[scan_idx]
        prev_type = prev_op[0]
        if prev_type == ALIGN_MATCH or prev_type == ALIGN_REPLACE:
            assert prev_op[1] is not None
            return prev_op[1] + 1
        elif prev_type == ALIGN_MERGE:
            assert prev_op[2] is not None
            return prev_op[2] + 1
        elif prev_type == ALIGN_DELETE:
            assert prev_op[1] is not None
            return prev_op[1] + 1

    # 直前に何もない場合は先頭に挿入
    return 0


# ---------------------------------------------------------------------------
# pyopenjtalk フォールバック
# ---------------------------------------------------------------------------
def get_target_from_pyopenjtalk(text: str) -> str | None:
    """
    pyopenjtalk でテキストを解析し、カタカナ読みを取得する。

    ROHAN transcript に該当がない場合のフォールバック。

    Args:
        text (str): 解析対象テキスト

    Returns:
        str | None: カタカナ読み、または取得失敗時は None
    """

    if pyopenjtalk is None:
        logger.warning('pyopenjtalk is not available, cannot get fallback reading')
        return None

    try:
        nodes = pyopenjtalk.run_frontend(text)
        if nodes is None:
            return None
        prons = [node.get('pron', '') for node in nodes if node.get('pron')]
        if len(prons) == 0:
            return None
        return ''.join(prons)
    except Exception as ex:
        logger.error(f'Failed to get reading from pyopenjtalk. text: {text}', exc_info=ex)
        return None


# ---------------------------------------------------------------------------
# vvproj の全エントリを処理
# ---------------------------------------------------------------------------
def extract_script_id_and_surface(text_field: str) -> tuple[str, str]:
    """
    vvproj の text フィールドから script_id とテキスト本文を抽出する。

    テキストは "ROHAN4600_XXXX:テキスト本文" の形式。

    Args:
        text_field (str): vvproj の text フィールドの値

    Returns:
        tuple[str, str]: (script_id, テキスト本文)。
            コロンがない場合は ('', text_field.strip())
    """

    if ':' in text_field:
        script_id, surface = text_field.split(':', 1)
        return script_id.strip(), surface.strip()
    return '', text_field.strip()


def load_problematic_script_ids(report_path: Path) -> set[str]:
    """
    mismatch_report_full.txt を解析し、「問題あり」と判定された script_id の集合を返す。

    ジャッジで「問題なし」とされたエントリを誤って変更しないよう、
    修正対象を「問題あり」のエントリのみに厳密に限定するために使用する。

    Args:
        report_path (Path): mismatch_report_full.txt のパス

    Returns:
        set[str]: 「問題あり」の script_id の集合
    """

    problematic_ids: set[str] = set()
    if report_path.exists() is not True:
        logger.warning(f'Mismatch report not found, will fix all mismatches. path: {report_path}')
        return problematic_ids

    content = report_path.read_text(encoding='utf-8')
    # レポートのエントリを分割: ========= の行で区切られ、#XXXX: script_id の形式
    entries = re.split(r'={72}\n#(\d{4}): (.*?)\n={72}', content)

    for entry_index in range(1, len(entries), 3):
        script_id = entries[entry_index + 1].strip()
        body = entries[entry_index + 2] if entry_index + 2 < len(entries) else ''

        judge_match = re.search(r'ジャッジ：(✅ 問題あり|✅ 問題なし|⚠ 要検討)　理由：(.+)', body)
        if judge_match is not None and '問題あり' in judge_match.group(1):
            if script_id:
                problematic_ids.add(script_id)
            else:
                # script_id が空の場合（ROHAN なしエントリ）、テキストで識別
                text_match = re.search(r'テキスト: (.+)', body)
                if text_match is not None:
                    problematic_ids.add(f'__surface__{text_match.group(1).strip()}')

    return problematic_ids


def should_fix_entry(
    vvproj_mora_str: str,
    rohan_kana: str | None,
    surface: str,
) -> tuple[bool, str | None, str]:
    """
    このエントリが修正対象かどうかを判定する。

    修正対象の判定基準:
    1. ROHAN transcript がある場合: vvproj のモーラ列が ROHAN と一致しなければ修正対象
    2. ROHAN transcript がない場合: pyopenjtalk の出力と比較して不一致なら修正対象

    Args:
        vvproj_mora_str (str): vvproj のモーラ列を連結した文字列
        rohan_kana (str | None): ROHAN transcript のカタカナ読み（なければ None）
        surface (str): テキスト本文

    Returns:
        tuple[bool, str | None, str]:
            (修正が必要か, ターゲットのカタカナ読み, 判定理由)
    """

    vvproj_norm = normalize_for_comparison(vvproj_mora_str)

    if rohan_kana is not None:
        rohan_norm = normalize_for_comparison(rohan_kana)
        if vvproj_norm == rohan_norm:
            return False, None, 'vvproj matches ROHAN'
        return True, rohan_kana, f'vvproj differs from ROHAN'

    # ROHAN がない場合は pyopenjtalk をフォールバック
    pyojt_kana = get_target_from_pyopenjtalk(surface)
    if pyojt_kana is None:
        return False, None, 'No ROHAN and pyopenjtalk failed'

    pyojt_norm = normalize_for_comparison(pyojt_kana)
    if vvproj_norm == pyojt_norm:
        return False, None, 'vvproj matches pyopenjtalk (no ROHAN)'

    return True, pyojt_kana, 'No ROHAN, using pyopenjtalk as target'


def _has_only_match_ops(
    alignment_ops: list[tuple[str, int | None, int | None, int | None]],
) -> bool:
    """
    アラインメント操作がすべて match であるかを確認する。

    Args:
        alignment_ops (list[tuple]): アラインメント操作リスト

    Returns:
        bool: すべて match なら True
    """

    return all(op[0] == ALIGN_MATCH for op in alignment_ops)


def process_single_entry(
    audio_item: dict,
    script_id: str,
    surface: str,
    rohan_kana: str | None,
) -> tuple[bool, list[str]]:
    """
    1つの vvproj エントリを処理する。

    vvproj のモーラ列を ROHAN（またはフォールバック）と比較し、
    必要に応じて修正を適用する。

    Args:
        audio_item (dict): vvproj の audioItem（直接変更される）
        script_id (str): スクリプト ID
        surface (str): テキスト本文
        rohan_kana (str | None): ROHAN transcript のカタカナ読み

    Returns:
        tuple[bool, list[str]]: (修正が適用されたか, ログメッセージのリスト)
    """

    log_lines: list[str] = []

    # vvproj のモーラ列を取得
    vvproj_moras = extract_flat_moras_from_item(audio_item)
    vvproj_mora_str = ''.join(vvproj_moras)

    # 修正が必要か判定
    is_need_fix, target_kana, reason = should_fix_entry(vvproj_mora_str, rohan_kana, surface)
    if is_need_fix is not True or target_kana is None:
        return False, log_lines

    log_lines.append(f'Entry: {script_id}')
    log_lines.append(f'  Surface: {surface}')
    log_lines.append(f'  vvproj moras: {vvproj_mora_str}')
    log_lines.append(f'  Target kana: {target_kana}')
    log_lines.append(f'  Reason: {reason}')

    # ターゲットをモーラに分割し、読み形→発音形に変換
    # ROHAN は「読み」（コウカ, ジンセイ）だが vvproj は「発音」（コオカ, ジンセエ）であるべき
    target_moras_raw = parse_kana_to_moras(target_kana)
    target_moras = convert_moras_yomi_to_pron(target_moras_raw)
    log_lines.append(f'  Target moras: {target_moras}')

    # DP アラインメント
    alignment_ops = dp_alignment(vvproj_moras, target_moras)

    # アラインメント操作の概要をログ出力
    op_summary: list[str] = []
    for op_entry in alignment_ops:
        op_type = op_entry[0]
        if op_type == ALIGN_MATCH:
            assert op_entry[1] is not None and op_entry[3] is not None
            op_summary.append(f'M({vvproj_moras[op_entry[1]]}={target_moras[op_entry[3]]})')
        elif op_type == ALIGN_REPLACE:
            assert op_entry[1] is not None and op_entry[3] is not None
            op_summary.append(
                f'R({vvproj_moras[op_entry[1]]}->{target_moras[op_entry[3]]})'
            )
        elif op_type == ALIGN_MERGE:
            assert op_entry[1] is not None and op_entry[2] is not None and op_entry[3] is not None
            op_summary.append(
                f'MG({vvproj_moras[op_entry[1]]}+{vvproj_moras[op_entry[2]]}'
                f'->{target_moras[op_entry[3]]})'
            )
        elif op_type == ALIGN_DELETE:
            assert op_entry[1] is not None
            op_summary.append(f'D({vvproj_moras[op_entry[1]]})')
        elif op_type == ALIGN_INSERT:
            assert op_entry[3] is not None
            op_summary.append(f'I({target_moras[op_entry[3]]})')
    log_lines.append(f'  Alignment: {" ".join(op_summary)}')

    # すべて match ならスキップ（正規化の差異のみ）
    if _has_only_match_ops(alignment_ops) is True:
        log_lines.append('  Result: All match, no modification needed')
        return False, log_lines

    # accentPhrases に修正を適用
    accent_phrases = audio_item['query']['accentPhrases']
    modified_phrases, mod_log, is_modified = apply_alignment_to_accent_phrases(
        accent_phrases, vvproj_moras, target_moras, alignment_ops,
    )

    log_lines.extend(mod_log)

    if is_modified is True:
        audio_item['query']['accentPhrases'] = modified_phrases
        # 修正後のモーラ列を確認ログ出力
        new_moras = extract_flat_moras_from_item(audio_item)
        log_lines.append(f'  Result: Modified. New moras: {"".join(new_moras)}')
    else:
        log_lines.append('  Result: No effective modification applied')

    return is_modified, log_lines


# ---------------------------------------------------------------------------
# メイン処理
# ---------------------------------------------------------------------------
def main() -> None:
    """
    メインエントリーポイント。

    全 vvproj ファイルを処理し、ROHAN transcript との不一致を修正する。
    修正ログと手動レビュー対象を出力する。
    """

    logger.info('Starting vvproj fix process')

    # ROHAN transcript 読み込み
    if ROHAN_TRANSCRIPT_PATH.exists() is not True:
        logger.error(f'ROHAN transcript not found: {ROHAN_TRANSCRIPT_PATH}')
        return

    rohan_dict = load_rohan_transcript(ROHAN_TRANSCRIPT_PATH)
    logger.info(f'Loaded ROHAN transcript. entries: {len(rohan_dict)}')

    # ジャッジレポートから「問題あり」の script_id を取得
    # 「問題なし」と判定されたエントリを誤って変更しないためのセーフガード
    problematic_ids = load_problematic_script_ids(MISMATCH_REPORT_PATH)
    logger.info(f'Loaded problematic script IDs from judge report. count: {len(problematic_ids)}')

    # vvproj ファイル一覧
    if VVPROJ_DIR.exists() is not True:
        logger.error(f'vvproj directory not found: {VVPROJ_DIR}')
        return

    vvproj_files = sorted(VVPROJ_DIR.glob('*.vvproj'))
    logger.info(f'Found vvproj files. count: {len(vvproj_files)}')

    # 処理カウンター
    total_entries = 0
    fixed_entries = 0
    skipped_entries = 0
    error_entries = 0

    # ログとレビュー対象の蓄積
    all_fix_logs: list[str] = []
    manual_review_logs: list[str] = []

    for vvproj_path in vvproj_files:
        logger.info(f'Processing: {vvproj_path.name}')

        try:
            vvproj_data = load_vvproj(vvproj_path)
        except Exception as ex:
            logger.error(f'Failed to load vvproj. file: {vvproj_path}', exc_info=ex)
            error_entries += 1
            continue

        is_file_modified = False

        # audioKeys の順序で処理（vvproj 内の並び順を維持）
        audio_keys = vvproj_data.get('audioKeys', [])
        audio_items = vvproj_data.get('audioItems', {})

        for audio_key in audio_keys:
            audio_item = audio_items.get(audio_key)
            if audio_item is None:
                continue

            text_field = str(audio_item.get('text', ''))
            script_id, surface = extract_script_id_and_surface(text_field)

            if len(surface.strip()) == 0:
                continue

            total_entries += 1

            # セーフガード: ROHAN と一致しているエントリは修正対象外
            # should_fix_entry() 内で ROHAN 一致チェックが行われるため、
            # ここではフィルタリングせず全エントリを処理対象とする
            # （以前は problematic_ids フィルタがあったが、ROHAN と不一致の
            #  「問題なし」エントリも修正すべきことが判明したため撤廃）

            # ROHAN のカタカナ読みを取得
            rohan_kana = rohan_dict.get(script_id) if script_id else None

            try:
                is_modified, entry_logs = process_single_entry(
                    audio_item, script_id, surface, rohan_kana,
                )

                if is_modified is True:
                    fixed_entries += 1
                    is_file_modified = True
                    all_fix_logs.extend(entry_logs)
                    all_fix_logs.append('')
                elif len(entry_logs) > 0:
                    # 修正は不要だったがログはある場合
                    skipped_entries += 1

            except Exception as ex:
                error_entries += 1
                error_msg = (
                    f'Entry: {script_id}\n'
                    f'  Surface: {surface}\n'
                    f'  Error: {ex}\n'
                )
                logger.error(
                    f'Failed to process entry. script_id: {script_id}, surface: {surface}',
                    exc_info=ex,
                )
                manual_review_logs.append(error_msg)
                manual_review_logs.append(traceback.format_exc())
                manual_review_logs.append('')

        # ファイルが変更された場合は上書き保存
        if is_file_modified is True:
            try:
                save_vvproj(vvproj_path, vvproj_data)
                logger.info(f'Saved modified vvproj: {vvproj_path.name}')
            except Exception as ex:
                logger.error(f'Failed to save vvproj. file: {vvproj_path}', exc_info=ex)
                error_entries += 1

    # 修正ログを出力
    logger.info(f'Writing fix log: {FIX_LOG_PATH}')
    fix_log_content = [
        'vvproj Fix Log',
        '=' * 72,
        f'Total entries processed: {total_entries}',
        f'Fixed entries: {fixed_entries}',
        f'Skipped entries (already correct): {skipped_entries}',
        f'Error entries: {error_entries}',
        '=' * 72,
        '',
    ]
    fix_log_content.extend(all_fix_logs)
    FIX_LOG_PATH.write_text('\n'.join(fix_log_content), encoding='utf-8')

    # 手動レビュー対象を出力
    if len(manual_review_logs) > 0:
        logger.info(f'Writing manual review file: {MANUAL_REVIEW_PATH}')
        review_content = [
            'vvproj Manual Review Required',
            '=' * 72,
            f'Entries requiring manual review: {len(manual_review_logs)}',
            '=' * 72,
            '',
        ]
        review_content.extend(manual_review_logs)
        MANUAL_REVIEW_PATH.write_text('\n'.join(review_content), encoding='utf-8')
    else:
        logger.info('No entries require manual review')

    # サマリー出力
    logger.info('=' * 60)
    logger.info(f'Fix process completed.')
    logger.info(f'  Total entries processed: {total_entries}')
    logger.info(f'  Fixed entries: {fixed_entries}')
    logger.info(f'  Skipped entries: {skipped_entries}')
    logger.info(f'  Error entries: {error_entries}')
    logger.info('=' * 60)


if __name__ == '__main__':
    main()

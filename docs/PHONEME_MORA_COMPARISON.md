# ROHAN / VOICEVOX pyopenjtalk / pyopenjtalk-plus 音素・モーラ対応比較表

## 概要

- **ROHAN4600**: モーラバランス型コーパス。音素バランスを考慮し、出現しにくいモーラを意図的に含む。
- **VOICEVOX pyopenjtalk**: VOICEVOX/open_jtalk を submodule として使用。jpcommon_mora_list は グヮ, クヮ のみ（クァ, グァ, シィ, デェ, フュ は非対応）。
- **VOICEVOX ENGINE**: pyopenjtalk の出力を処理。mora_mapping に クァ, グァ, デェ はあるが、シィ, フュ は未定義。phoneme.py および text_analyzer の _OJT_CONSONANTS に `fy` 子音は含まれない。
- **pyopenjtalk-plus**: tsukumijima/open_jtalk の jpcommon_mora_list に基づく。クァ, グァ, シィ, デェ, フュ をすべて対応。

## レア音素の対応差（要注目）

| モーラ | 音素 (C+V) | ROHAN使用 | VOICEVOX | pyopenjtalk-plus |
|--------|------------|:---------:|:--------:|:----------------:|
| クァ | kw+a | ✓ | ✗ | ✓ |
| クィ | kw+i | ✓ | ✗ | ✓ |
| クゥ | kw+u | ✓ | ✗ | ✓ |
| クェ | kw+e | ✓ | ✗ | ✓ |
| クォ | kw+o | ✓ | ✗ | ✓ |
| クヮ | kw+a |  | ✓ | ✓ |
| グァ | gw+a | ✓ | ✗ | ✓ |
| グィ | gw+i | ✓ | ✗ | ✓ |
| グゥ | gw+u | ✓ | ✗ | ✓ |
| グェ | gw+e | ✓ | ✗ | ✓ |
| グォ | gw+o | ✓ | ✗ | ✓ |
| グヮ | gw+a |  | ✓ | ✓ |
| シィ | s+i | ✓ | ✗ | ✓ |
| デェ | dy+e | ✓ | ✗ | ✓ |
| フュ | fy+u | ✓ | ✗ | ✓ |

## ROHAN で使用されているが VOICEVOX で非対応のモーラ

| モーラ | pyopenjtalk-plus 音素 |
|--------|----------------------|
| クァ | kw+a |
| クィ | kw+i |
| クゥ | kw+u |
| クェ | kw+e |
| クォ | kw+o |
| グァ | gw+a |
| グィ | gw+i |
| グゥ | gw+u |
| グェ | gw+e |
| グォ | gw+o |
| シィ | s+i |
| デェ | dy+e |
| フュ | fy+u |

## pyopenjtalk-plus が追加しているモーラ（VOICEVOX にない）

| モーラ | 音素 (C+V) |
|--------|------------|
| クァ | kw+a |
| クィ | kw+i |
| クゥ | kw+u |
| クェ | kw+e |
| クォ | kw+o |
| グァ | gw+a |
| グィ | gw+i |
| グゥ | gw+u |
| グェ | gw+e |
| グォ | gw+o |
| シィ | s+i |
| デェ | dy+e |
| フュ | fy+u |

## 全モーラ対応一覧（レア音素中心）

| モーラ | ROHAN | VOICEVOX | plus | 音素(plus) |
|--------|:-----:|:--------:|:----:|------------|
| ア | ✓ | ✓ | ✓ | a |
| イ | ✓ | ✓ | ✓ | i |
| イェ | ✓ | ✓ | ✓ | y+e |
| ウ | ✓ | ✓ | ✓ | u |
| ウィ | ✓ | ✓ | ✓ | w+i |
| ウェ | ✓ | ✓ | ✓ | w+e |
| ウォ | ✓ | ✓ | ✓ | w+o |
| エ | ✓ | ✓ | ✓ | e |
| オ | ✓ | ✓ | ✓ | o |
| カ | ✓ | ✓ | ✓ | k+a |
| ガ | ✓ | ✓ | ✓ | g+a |
| キ | ✓ | ✓ | ✓ | k+i |
| キェ | ✓ | ✓ | ✓ | ky+e |
| キャ | ✓ | ✓ | ✓ | ky+a |
| キュ | ✓ | ✓ | ✓ | ky+u |
| キョ | ✓ | ✓ | ✓ | ky+o |
| ギ | ✓ | ✓ | ✓ | g+i |
| ギェ | ✓ | ✓ | ✓ | gy+e |
| ギャ | ✓ | ✓ | ✓ | gy+a |
| ギュ | ✓ | ✓ | ✓ | gy+u |
| ギョ | ✓ | ✓ | ✓ | gy+o |
| ク | ✓ | ✓ | ✓ | k+u |
| クァ | ✓ | ✗ | ✓ | kw+a |
| クィ | ✓ | ✗ | ✓ | kw+i |
| クゥ | ✓ | ✗ | ✓ | kw+u |
| クェ | ✓ | ✗ | ✓ | kw+e |
| クォ | ✓ | ✗ | ✓ | kw+o |
| クヮ |  | ✓ | ✓ | kw+a |
| グ | ✓ | ✓ | ✓ | g+u |
| グァ | ✓ | ✗ | ✓ | gw+a |
| グィ | ✓ | ✗ | ✓ | gw+i |
| グゥ | ✓ | ✗ | ✓ | gw+u |
| グェ | ✓ | ✗ | ✓ | gw+e |
| グォ | ✓ | ✗ | ✓ | gw+o |
| グヮ |  | ✓ | ✓ | gw+a |
| ケ | ✓ | ✓ | ✓ | k+e |
| ゲ | ✓ | ✓ | ✓ | g+e |
| コ | ✓ | ✓ | ✓ | k+o |
| ゴ | ✓ | ✓ | ✓ | g+o |
| サ | ✓ | ✓ | ✓ | s+a |
| ザ | ✓ | ✓ | ✓ | z+a |
| シ | ✓ | ✓ | ✓ | sh+i |
| シィ | ✓ | ✗ | ✓ | s+i |
| シェ | ✓ | ✓ | ✓ | sh+e |
| シャ | ✓ | ✓ | ✓ | sh+a |
| シュ | ✓ | ✓ | ✓ | sh+u |
| ショ | ✓ | ✓ | ✓ | sh+o |
| ジ | ✓ | ✓ | ✓ | j+i |
| ジェ | ✓ | ✓ | ✓ | j+e |
| ジャ | ✓ | ✓ | ✓ | j+a |
| ジュ | ✓ | ✓ | ✓ | j+u |
| ジョ | ✓ | ✓ | ✓ | j+o |
| ス | ✓ | ✓ | ✓ | s+u |
| スィ | ✓ | ✓ | ✓ | s+i |
| ズ | ✓ | ✓ | ✓ | z+u |
| ズィ | ✓ | ✓ | ✓ | z+i |
| セ | ✓ | ✓ | ✓ | s+e |
| ゼ | ✓ | ✓ | ✓ | z+e |
| ソ | ✓ | ✓ | ✓ | s+o |
| ゾ | ✓ | ✓ | ✓ | z+o |
| タ | ✓ | ✓ | ✓ | t+a |
| ダ | ✓ | ✓ | ✓ | d+a |
| チ | ✓ | ✓ | ✓ | ch+i |
| チェ | ✓ | ✓ | ✓ | ch+e |
| チャ | ✓ | ✓ | ✓ | ch+a |
| チュ | ✓ | ✓ | ✓ | ch+u |
| チョ | ✓ | ✓ | ✓ | ch+o |
| ヂ | ✓ | ✓ | ✓ | j+i |
| ツ | ✓ | ✓ | ✓ | ts+u |
| ツァ | ✓ | ✓ | ✓ | ts+a |
| ツィ | ✓ | ✓ | ✓ | ts+i |
| ツェ | ✓ | ✓ | ✓ | ts+e |
| ツォ | ✓ | ✓ | ✓ | ts+o |
| ヅ | ✓ | ✓ | ✓ | z+u |
| テ | ✓ | ✓ | ✓ | t+e |
| ティ | ✓ | ✓ | ✓ | t+i |
| テャ | ✓ | ✓ | ✓ | ty+a |
| テュ | ✓ | ✓ | ✓ | ty+u |
| テョ | ✓ | ✓ | ✓ | ty+o |
| デ | ✓ | ✓ | ✓ | d+e |
| ディ | ✓ | ✓ | ✓ | d+i |
| デェ | ✓ | ✗ | ✓ | dy+e |
| デャ | ✓ | ✓ | ✓ | dy+a |
| デュ | ✓ | ✓ | ✓ | dy+u |
| デョ | ✓ | ✓ | ✓ | dy+o |
| ト | ✓ | ✓ | ✓ | t+o |
| トゥ | ✓ | ✓ | ✓ | t+u |
| ド | ✓ | ✓ | ✓ | d+o |
| ドゥ | ✓ | ✓ | ✓ | d+u |
| ナ | ✓ | ✓ | ✓ | n+a |
| ニ | ✓ | ✓ | ✓ | n+i |
| ニェ | ✓ | ✓ | ✓ | ny+e |
| ニャ | ✓ | ✓ | ✓ | ny+a |
| ニュ | ✓ | ✓ | ✓ | ny+u |
| ニョ | ✓ | ✓ | ✓ | ny+o |
| ヌ | ✓ | ✓ | ✓ | n+u |
| ネ | ✓ | ✓ | ✓ | n+e |
| ノ | ✓ | ✓ | ✓ | n+o |
| ハ | ✓ | ✓ | ✓ | h+a |
| バ | ✓ | ✓ | ✓ | b+a |
| パ | ✓ | ✓ | ✓ | p+a |
| ヒ | ✓ | ✓ | ✓ | h+i |
| ヒェ | ✓ | ✓ | ✓ | hy+e |
| ヒャ | ✓ | ✓ | ✓ | hy+a |
| ヒュ | ✓ | ✓ | ✓ | hy+u |
| ヒョ | ✓ | ✓ | ✓ | hy+o |
| ビ | ✓ | ✓ | ✓ | b+i |
| ビェ | ✓ | ✓ | ✓ | by+e |
| ビャ | ✓ | ✓ | ✓ | by+a |
| ビュ | ✓ | ✓ | ✓ | by+u |
| ビョ | ✓ | ✓ | ✓ | by+o |
| ピ | ✓ | ✓ | ✓ | p+i |
| ピェ | ✓ | ✓ | ✓ | py+e |
| ピャ | ✓ | ✓ | ✓ | py+a |
| ピュ | ✓ | ✓ | ✓ | py+u |
| ピョ | ✓ | ✓ | ✓ | py+o |
| フ | ✓ | ✓ | ✓ | f+u |
| ファ | ✓ | ✓ | ✓ | f+a |
| フィ | ✓ | ✓ | ✓ | f+i |
| フェ | ✓ | ✓ | ✓ | f+e |
| フォ | ✓ | ✓ | ✓ | f+o |
| フュ | ✓ | ✗ | ✓ | fy+u |
| ブ | ✓ | ✓ | ✓ | b+u |
| プ | ✓ | ✓ | ✓ | p+u |
| ヘ | ✓ | ✓ | ✓ | h+e |
| ベ | ✓ | ✓ | ✓ | b+e |
| ペ | ✓ | ✓ | ✓ | p+e |
| ホ | ✓ | ✓ | ✓ | h+o |
| ボ | ✓ | ✓ | ✓ | b+o |
| ポ | ✓ | ✓ | ✓ | p+o |
| マ | ✓ | ✓ | ✓ | m+a |
| ミ | ✓ | ✓ | ✓ | m+i |
| ミェ | ✓ | ✓ | ✓ | my+e |
| ミャ | ✓ | ✓ | ✓ | my+a |
| ミュ | ✓ | ✓ | ✓ | my+u |
| ミョ | ✓ | ✓ | ✓ | my+o |
| ム | ✓ | ✓ | ✓ | m+u |
| メ | ✓ | ✓ | ✓ | m+e |
| モ | ✓ | ✓ | ✓ | m+o |
| ヤ | ✓ | ✓ | ✓ | y+a |
| ユ | ✓ | ✓ | ✓ | y+u |
| ヨ | ✓ | ✓ | ✓ | y+o |
| ラ | ✓ | ✓ | ✓ | r+a |
| リ | ✓ | ✓ | ✓ | r+i |
| リェ | ✓ | ✓ | ✓ | ry+e |
| リャ | ✓ | ✓ | ✓ | ry+a |
| リュ | ✓ | ✓ | ✓ | ry+u |
| リョ | ✓ | ✓ | ✓ | ry+o |
| ル | ✓ | ✓ | ✓ | r+u |
| レ | ✓ | ✓ | ✓ | r+e |
| ロ | ✓ | ✓ | ✓ | r+o |
| ワ | ✓ | ✓ | ✓ | w+a |
| ヲ | ✓ | ✓ | ✓ | o |
| ヴ | ✓ | ✓ | ✓ | v+u |
| ヴァ | ✓ | ✓ | ✓ | v+a |
| ヴィ | ✓ | ✓ | ✓ | v+i |
| ヴェ | ✓ | ✓ | ✓ | v+e |
| ヴォ | ✓ | ✓ | ✓ | v+o |

## 出典（ソースコード参照）

調査対象リポジトリは `/tmp/voicevox_investigation/` にクローンしたものを使用。以下はその相対パス。

### VOICEVOX open_jtalk (VOICEVOX pyopenjtalk が使用)

| ファイル | 内容 |
|----------|------|
| `voicevox_open_jtalk/src/jpcommon/jpcommon_rule_utf_8.h` L72-234 | `jpcommon_mora_list[]` 定義。クヮ, グヮ のみ（L203-204）。クァ, グァ, シィ, デェ, フュ は含まれない。 |
| `voicevox_open_jtalk/src/jpcommon/jpcommon_label.c` L507-585 | pron を `jpcommon_mora_list` で照合。未登録モーラは L584「wrong mora list」で break。 |

### tsukumijima open_jtalk (pyopenjtalk-plus が使用)

| ファイル | 内容 |
|----------|------|
| `tsukumijima_open_jtalk/src/jpcommon/jpcommon_rule_utf_8.h` L76-252 | `jpcommon_mora_list[]` 定義。L76-90 で クァ, クィ, クゥ, クェ, クォ, クヮ, グァ, グィ, グゥ, グェ, グォ, グヮ, デェ, シィ, フュ を先頭に追加。 |

### VOICEVOX ENGINE

| ファイル | 内容 |
|----------|------|
| `voicevox_engine/tts_pipeline/phoneme.py` L15-49 | `Consonant` 型定義。`fy` は含まれない。 |
| `voicevox_engine/tts_pipeline/text_analyzer.py` L47-81 | `_OJT_CONSONANTS` 定義。`fy` は含まれない。OpenJTalk 出力の音素バリデーションに使用。 |
| `voicevox_engine/tts_pipeline/mora_mapping.py` L52-413 | `_MoraKana`, `_mora_list_minimum`, `_mora_list_additional`。クァ, グァ, デェ はあるが、シィ, フュ は未定義。 |

### ROHAN

| ファイル | 内容 |
|----------|------|
| `rohan_transcript_utf8.txt` | Rohan4600_transcript_utf8.txt。モーラバランス設計で クァ, グァ, シィ, デェ, フュ などを意図的に使用。 |

---

### 補足

- **VOICEVOX の実質的な対応**: pyopenjtalk の pron（カタカナ）は jpcommon の `jpcommon_mora_list` で照合される。VOICEVOX open_jtalk は グヮ, クヮ のみ持つため、辞書が クァ を出力しても jpcommon は照合に失敗し「wrong mora list」でエラーとなる。
- **VOICEVOX ENGINE mora_mapping**: 音素→カタカナ表示用。クァ, グァ, デェ は定義されているが、pyopenjtalk からはこれらは出力されないため、実質的には外部入力（例: ユーザー辞書の手動指定）用。
- **フュ (fy+u)**: VOICEVOX では `phoneme.py` に `fy` がなく、`text_analyzer` の `_OJT_CONSONANTS` にも含まれない。pyopenjtalk-plus が フュ を出力しても、VOICEVOX ENGINE は `NonOjtPhonemeError` を発生させる。
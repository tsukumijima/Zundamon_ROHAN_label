# VOICEVOX ENGINE のモーラ・音素変換ロジック調査レポート

本ドキュメントは、VOICEVOX ENGINE のソースコード（`/tmp/voicevox_investigation/` にクローン）を解析し、
テキストからモーラ・音素への変換がどのように行われているかを**推測ではなく根拠付きで**まとめたものである。

## 1. 変換フロー全体像

```
テキスト
  → pyopenjtalk.run_frontend(text)  [VOICEVOX/pyopenjtalk]
  → MeCab (辞書: open_jtalk_dic_utf_8-1.11 / naist-jdic)
  → NJD (mecab2njd)
  → pyopenjtalk.make_label(njd_features)
  → OpenJTalk C コード (jpcommon_label.c)
  → フルコンテキストラベル
  → VOICEVOX ENGINE text_analyzer
  → AccentPhrase (モーラ列)
```

## 2. 各段階の詳細

### 2.1 読み（pron）の取得元

**出典**: `voicevox_engine/tts_pipeline/njd_feature_processor.py` L95

```python
njd_features = list(map(lambda f: NjdFeature(**f), pyopenjtalk.run_frontend(text)))
```

`pyopenjtalk.run_frontend()` は内部で MeCab を呼び出し、各トークンの `pron`（カタカナ読み）を返す。
**`pron` は MeCab 辞書（naist-jdic）に登録された読みそのものである。**

### 2.2 MeCab 辞書

- **辞書名**: `open_jtalk_dic_utf_8-1.11`（r9y9/open_jtalk のリリースから取得）
- **実体**: `mecab-naist-jdic` の `naist-jdic.csv`
- **役割**: 表層形 → 読み（カタカナ）の対応を保持。MeCab は形態素解析時にこの辞書を参照する。

### 2.3 OpenJTalk のモーラ→音素変換

**出典**: `open_jtalk/src/jpcommon/jpcommon_rule_utf_8.h` の `jpcommon_mora_list`

`jpcommon_label.c` の `JPCommonLabel_push_word()` は、`pron`（カタカナ列）を先頭から `jpcommon_mora_list` で照合し、
マッチしたモーラを [子音, 母音] の音素列に変換する。

**jpcommon_mora_list に含まれるレア音素の例**（r9y9 と VOICEVOX で同一）:

| モーラ | 子音 | 母音 |
|--------|------|------|
| グヮ | gw | a |
| クヮ | kw | a |
| デョ | dy | o |
| デュ | dy | u |
| デャ | dy | a |
| テョ | ty | o |
| テュ | ty | u |
| テャ | ty | a |
| ツォ | ts | o |
| ツェ | ts | e |
| ツィ | ts | i |
| ツァ | ts | a |
| スィ | s | i |
| ズィ | z | i |
| シェ | sh | e |
| ジェ | j | e |
| ヴァ〜ヴョ | v / by | a,i,u,e,o 等 |

**結論**: OpenJTalk の C コードは、辞書が正しいカタカナ読みを出力すれば、グヮ・クヮ・ティ・ディ等のレア音素を正しく扱える。

### 2.4 VOICEVOX ENGINE の音素バリデーション

**出典**: `voicevox_engine/tts_pipeline/text_analyzer.py` L49-82

`_OJT_CONSONANTS` に `gw`, `kw`, `dy`, `ty` 等が含まれており、VOICEVOX ENGINE はこれらの音素を**受け入れる**。
「レア音素に対応していない」という表現は不正確である。対応している。

## 3. 「基肥 → キヒ」の原因（根拠付き）

### 3.1 辞書の登録内容

**出典**: `r9y9_open_jtalk/src/mecab-naist-jdic/naist-jdic.csv`（VOICEVOX/open_jtalk も同一）

```
185524:基肥,1345,1345,5746,名詞,一般,*,*,*,*,基肥,キヒ,キヒ,1/2,C3
103749:もとごえ,1345,1345,7433,名詞,一般,*,*,*,*,もとごえ,モトゴエ,モトゴエ,0/4,C2
```

- 「基肥」は辞書で **キヒ** と登録されている（誤り）
- 「もとごえ」は別語として **モトゴエ** で登録されている（正しい）

### 3.2 結論

**原因**: **meacb-naist-jdic（naist-jdic.csv）の辞書登録ミス**

- 基肥（農業用語: 播種・定植前に施す肥料）の正しい読みは「もとごえ」
- 辞書では「基肥」が「キヒ」と誤登録されている
- pyopenjtalk も OpenJTalk も、辞書が出力した「キヒ」をそのまま音素化しているだけである
- **pyopenjtalk や OpenJTalk の変換ロジックの誤りではない**

## 4. 931 件の不一致について

不一致は次のいずれかに分類できる:

| 分類 | 説明 | 例 |
|------|------|-----|
| 辞書誤登録 | naist-jdic に誤った読みが登録されている | 基肥→キヒ、語→ゴ |
| 未知語 | 辞書にない語の読み推定が不正確 | 固有名詞、専門用語 |
| 人力補正 | vvproj 側で意図的に修正した正しい読み | アクセント・読みの手動修正 |
| vvproj 誤り | vvproj 側の誤記入・誤修正 | 修正すべき |

「pyopenjtalk が悪い」と一言でまとめるのは不正確である。多くの場合は**辞書（naist-jdic）の登録内容**が読みの正誤を決めている。

## 5. 参照したソースコード

- `/tmp/voicevox_investigation/voicevox_engine/` … VOICEVOX/voicevox_engine
- `/tmp/voicevox_investigation/voicevox_pyopenjtalk/` … VOICEVOX/pyopenjtalk
- `/tmp/voicevox_investigation/voicevox_open_jtalk/` … VOICEVOX/open_jtalk
- `/tmp/voicevox_investigation/r9y9_open_jtalk/` … r9y9/open_jtalk（比較用）

調査日: 2025-03-13

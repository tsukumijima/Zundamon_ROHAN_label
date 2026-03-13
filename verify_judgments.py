"""
ダブルチェック用検証スクリプト。
mismatch_report_full.txt の全エントリを構造化解析し、
ジャッジの妥当性を自動検証する。
"""

import re
from collections import Counter


def parse_report(filepath: str) -> list[dict]:
    """レポートファイルを解析して全エントリを辞書リストとして返す。"""

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    entries = re.split(r'={72}\n#(\d{4}): (.*?)\n={72}', content)

    parsed = []
    for i in range(1, len(entries), 3):
        num = int(entries[i])
        script_id = entries[i + 1].strip()
        body = entries[i + 2] if i + 2 < len(entries) else ''

        judge_match = re.search(r'ジャッジ：(✅ 問題あり|✅ 問題なし|⚠ 要検討)　理由：(.+)', body)
        judge = judge_match.group(1) if judge_match else 'UNKNOWN'
        reason = judge_match.group(2) if judge_match else ''

        # ROHAN / pyopenjtalk / vvproj の正規化後の値を取得
        # 各行が改行を挟むため re.DOTALL で .* が改行をまたぐようにする
        rohan_norm_match = re.search(r'ROHAN \(正\):.*?\(正規化後: (.+?)\)', body, re.DOTALL)
        rohan_norm = rohan_norm_match.group(1) if rohan_norm_match else ''

        pyojt_norm_match = re.search(r'pyopenjtalk 出力:.*?\(正規化後: (.+?)\)', body, re.DOTALL)
        pyojt_norm = pyojt_norm_match.group(1) if pyojt_norm_match else ''

        vvproj_norm_match = re.search(r'vvproj モーラ:.*?\(正規化後: (.+?)\)', body, re.DOTALL)
        vvproj_norm = vvproj_norm_match.group(1) if vvproj_norm_match else ''

        text_match = re.search(r'テキスト: (.+)', body)
        text = text_match.group(1) if text_match else ''

        parsed.append({
            'num': num,
            'script_id': script_id,
            'judge': judge,
            'reason': reason,
            'rohan_norm': rohan_norm,
            'pyojt_norm': pyojt_norm,
            'vvproj_norm': vvproj_norm,
            'text': text,
        })

    return parsed


def levenshtein_distance(a: str, b: str) -> int:
    """レーベンシュタイン距離を計算する。"""

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


def main() -> None:
    """全件検証を実行する。"""

    parsed = parse_report('mismatch_report_full.txt')
    print(f'Total parsed entries: {len(parsed)}')

    judge_counts = Counter(e['judge'] for e in parsed)
    for judge_label, count in judge_counts.items():
        print(f'  {judge_label}: {count}')

    # レア音素ペア
    rare_pairs = [
        ('クァ', 'クア'), ('クィ', 'クイ'), ('クゥ', 'クウ'), ('クェ', 'クエ'), ('クォ', 'クオ'),
        ('グァ', 'グア'), ('グィ', 'グイ'), ('グゥ', 'グウ'), ('グェ', 'グエ'), ('グォ', 'グオ'),
        ('シィ', 'シイ'), ('デェ', 'デエ'), ('フュ', 'フユ'),
        ('イェ', 'イエ'), ('キェ', 'キエ'), ('ギェ', 'ギエ'),
    ]

    # 拗音・外来語音ペア（ェ/ュ/ャ/ョ 系の潰しを網羅）
    youon_pairs = [
        # 拗音（ャ/ュ/ョ 系）
        ('リャ', 'リヤ'), ('リュ', 'リユ'), ('リョ', 'リヨ'),
        ('ニャ', 'ニヤ'), ('ニュ', 'ニユ'), ('ニョ', 'ニヨ'),
        ('ミャ', 'ミヤ'), ('ミュ', 'ミユ'), ('ミョ', 'ミヨ'),
        ('ビャ', 'ビヤ'), ('ビュ', 'ビユ'), ('ビョ', 'ビヨ'),
        ('ピャ', 'ピヤ'), ('ピュ', 'ピユ'), ('ピョ', 'ピヨ'),
        ('ヒャ', 'ヒヤ'), ('ヒュ', 'ヒユ'), ('ヒョ', 'ヒヨ'),
        ('キャ', 'キヤ'), ('キュ', 'キユ'), ('キョ', 'キヨ'),
        ('ギャ', 'ギヤ'), ('ギュ', 'ギユ'), ('ギョ', 'ギヨ'),
        ('シャ', 'シヤ'), ('シュ', 'シユ'), ('ショ', 'シヨ'),
        ('ジャ', 'ジヤ'), ('ジュ', 'ジユ'), ('ジョ', 'ジヨ'),
        ('チャ', 'チヤ'), ('チュ', 'チユ'), ('チョ', 'チヨ'),
        ('テャ', 'テヤ'), ('テュ', 'テユ'), ('テョ', 'テヨ'),
        ('デャ', 'デヤ'), ('デュ', 'デユ'), ('デョ', 'デヨ'),
        # 外来語音（ェ 系）
        ('シェ', 'シエ'), ('ジェ', 'ジエ'), ('チェ', 'チエ'),
        ('ミェ', 'ミエ'), ('ビェ', 'ビエ'), ('ヒェ', 'ヒエ'),
        ('ピェ', 'ピエ'), ('リェ', 'リエ'), ('ニェ', 'ニエ'),
        # 外来語音（その他）
        ('スィ', 'スイ'), ('ズィ', 'ズイ'),
        ('ツァ', 'ツア'), ('ツィ', 'ツイ'), ('ツェ', 'ツエ'), ('ツォ', 'ツオ'),
        ('ファ', 'フア'), ('フィ', 'フイ'), ('フェ', 'フエ'), ('フォ', 'フオ'),
        ('ウィ', 'ウイ'), ('ウェ', 'ウエ'), ('ウォ', 'ウオ'),
        ('ティ', 'テイ'), ('トゥ', 'トウ'), ('ディ', 'デイ'),
        ('ドゥ', 'ドウ'),
    ]

    # === CHECK 1: 問題なし but レア音素潰しあり ===
    print()
    print('=== CHECK 1: 問題なし but ROHAN のレア音素を vvproj が潰している ===')
    found = False
    for entry in parsed:
        if '問題なし' not in entry['judge'] or not entry['rohan_norm']:
            continue
        for rare, collapsed in rare_pairs:
            if rare in entry['rohan_norm'] and rare not in entry['vvproj_norm'] and collapsed in entry['vvproj_norm']:
                print(f"  #{entry['num']:04d}: {entry['text'][:50]} | ROHAN: {rare}, vvproj: {collapsed}")
                found = True
    if not found:
        print('  None found.')

    # === CHECK 2: 問題なし but 拗音潰しあり ===
    print()
    print('=== CHECK 2: 問題なし but ROHAN の拗音を vvproj が潰している ===')
    found = False
    for entry in parsed:
        if '問題なし' not in entry['judge'] or not entry['rohan_norm']:
            continue
        for rare, collapsed in youon_pairs:
            if rare in entry['rohan_norm'] and rare not in entry['vvproj_norm'] and collapsed in entry['vvproj_norm']:
                print(f"  #{entry['num']:04d}: {entry['text'][:50]} | ROHAN: {rare}, vvproj: {collapsed}")
                found = True
    if not found:
        print('  None found.')

    # === CHECK 3: 問題あり but ヅ/ズ 表記ゆれのみ ===
    print()
    print('=== CHECK 3: 問題あり but ヅ/ズ 表記ゆれのみ (should be 問題なし?) ===')
    found = False
    for entry in parsed:
        if '問題あり' not in entry['judge'] or not entry['rohan_norm']:
            continue
        if 'ヅ' in entry['rohan_norm'] and 'ズ' in entry['vvproj_norm']:
            temp = entry['vvproj_norm'].replace('ズ', 'ヅ')
            if temp == entry['rohan_norm']:
                print(f"  #{entry['num']:04d}: {entry['text'][:50]}")
                found = True
    if not found:
        print('  None found.')

    # === CHECK 4: 要検討 entries ===
    print()
    print('=== CHECK 4: 要検討 entries ===')
    found = False
    for entry in parsed:
        if '要検討' in entry['judge']:
            print(f"  #{entry['num']:04d}: {entry['text'][:60]} | {entry['reason']}")
            found = True
    if not found:
        print('  None found.')

    # === CHECK 5: 問題あり but vvproj == ROHAN ===
    print()
    print('=== CHECK 5: 問題あり but vvproj == ROHAN (should be 問題なし) ===')
    found = False
    for entry in parsed:
        if '問題あり' in entry['judge'] and entry['rohan_norm'] and entry['vvproj_norm'] == entry['rohan_norm']:
            print(f"  #{entry['num']:04d}: {entry['text'][:50]}")
            found = True
    if not found:
        print('  None found.')

    # === CHECK 6: 問題なし but pyopenjtalk == ROHAN ===
    print()
    print('=== CHECK 6: 問題なし but pyopenjtalk == ROHAN (should be 問題あり?) ===')
    found = False
    for entry in parsed:
        if '問題なし' not in entry['judge']:
            continue
        if entry['rohan_norm'] and entry['pyojt_norm'] == entry['rohan_norm'] and entry['vvproj_norm'] != entry['rohan_norm']:
            print(f"  #{entry['num']:04d}: {entry['text'][:50]} | {entry['reason'][:60]}")
            found = True
    if not found:
        print('  None found.')

    # === CHECK 7: ヂ/ジ 表記ゆれの確認 ===
    print()
    print('=== CHECK 7: 問題あり but ヂ/ジ 表記ゆれのみ (should be 問題なし?) ===')
    found = False
    for entry in parsed:
        if '問題あり' not in entry['judge'] or not entry['rohan_norm']:
            continue
        if 'ヂ' in entry['rohan_norm'] and 'ジ' in entry['vvproj_norm']:
            temp = entry['vvproj_norm'].replace('ジ', 'ヂ')
            if temp == entry['rohan_norm']:
                print(f"  #{entry['num']:04d}: {entry['text'][:50]}")
                found = True
    if not found:
        print('  None found.')

    # === CHECK 8: ROHAN なし entries の判定確認 ===
    print()
    print('=== CHECK 8: ROHAN なし entries の判定分布 ===')
    no_rohan = [e for e in parsed if not e['rohan_norm']]
    no_rohan_counts = Counter(e['judge'] for e in no_rohan)
    print(f'  Total ROHAN なし: {len(no_rohan)}')
    for judge_label, count in no_rohan_counts.items():
        print(f'    {judge_label}: {count}')

    # === CHECK 9: 距離情報を含むジャッジの一貫性 ===
    print()
    print('=== CHECK 9: 距離ジャッジで vvproj 側が近い but 問題あり ===')
    found = False
    for entry in parsed:
        if '問題あり' in entry['judge'] and 'vvproj の方が ROHAN に近い' in entry['reason']:
            print(f"  #{entry['num']:04d}: {entry['text'][:50]} | {entry['reason'][:60]}")
            found = True
    if not found:
        print('  None found.')

    print()
    print('=== CHECK 10: 距離ジャッジで pyojt 側が近い but 問題なし ===')
    found = False
    for entry in parsed:
        if '問題なし' in entry['judge'] and 'pyopenjtalk の方が ROHAN に近い' in entry['reason']:
            print(f"  #{entry['num']:04d}: {entry['text'][:50]} | {entry['reason'][:60]}")
            found = True
    if not found:
        print('  None found.')

    # === CHECK 11: UNKNOWN ジャッジ (パース失敗) ===
    print()
    print('=== CHECK 11: UNKNOWN ジャッジ (パース失敗) ===')
    unknowns = [e for e in parsed if e['judge'] == 'UNKNOWN']
    if unknowns:
        for entry in unknowns:
            print(f"  #{entry['num']:04d}: {entry['text'][:50]}")
    else:
        print('  None found.')

    # === CHECK 12: 問題あり but vvproj と ROHAN の差が ヅ/ズ のみ（部分一致含む） ===
    print()
    print('=== CHECK 12: 問題あり entries where vvproj/ROHAN diff includes ヅ/ズ only ===')
    found = False
    for entry in parsed:
        if '問題あり' not in entry['judge'] or not entry['rohan_norm']:
            continue
        # ヅ/ズ の差を正規化した上で比較
        rohan_dz_normalized = entry['rohan_norm'].replace('ヅ', 'ズ')
        vvproj_dz_normalized = entry['vvproj_norm'].replace('ヅ', 'ズ')
        if rohan_dz_normalized == vvproj_dz_normalized and entry['vvproj_norm'] != entry['rohan_norm']:
            print(f"  #{entry['num']:04d}: {entry['text'][:60]}")
            print(f"    ROHAN:  {entry['rohan_norm'][:60]}")
            print(f"    vvproj: {entry['vvproj_norm'][:60]}")
            found = True
    if not found:
        print('  None found.')

    # === CHECK 13: 問題あり but vvproj と ROHAN の差が ヂ/ジ のみ ===
    print()
    print('=== CHECK 13: 問題あり entries where vvproj/ROHAN diff is ヂ/ジ only ===')
    found = False
    for entry in parsed:
        if '問題あり' not in entry['judge'] or not entry['rohan_norm']:
            continue
        rohan_dj_normalized = entry['rohan_norm'].replace('ヂ', 'ジ')
        vvproj_dj_normalized = entry['vvproj_norm'].replace('ヂ', 'ジ')
        if rohan_dj_normalized == vvproj_dj_normalized and entry['vvproj_norm'] != entry['rohan_norm']:
            print(f"  #{entry['num']:04d}: {entry['text'][:60]}")
            print(f"    ROHAN:  {entry['rohan_norm'][:60]}")
            print(f"    vvproj: {entry['vvproj_norm'][:60]}")
            found = True
    if not found:
        print('  None found.')

    # === CHECK 14: 問題あり but vvproj と ROHAN の距離が 1 の entries ===
    # (距離が近いのに問題ありとされている → 内容確認必要)
    print()
    print('=== CHECK 14: 問題あり with distance(vvproj, ROHAN)=1, 何が 1 文字違うか ===')
    found = False
    for entry in parsed:
        if '問題あり' not in entry['judge'] or not entry['rohan_norm']:
            continue
        dist = levenshtein_distance(entry['vvproj_norm'], entry['rohan_norm'])
        if dist == 1:
            # 差分の文字を特定
            diff_chars = []
            rohan_chars = entry['rohan_norm']
            vvproj_chars = entry['vvproj_norm']
            for idx in range(max(len(rohan_chars), len(vvproj_chars))):
                rc = rohan_chars[idx] if idx < len(rohan_chars) else ''
                vc = vvproj_chars[idx] if idx < len(vvproj_chars) else ''
                if rc != vc:
                    diff_chars.append(f'{rc}→{vc}')
            print(f"  #{entry['num']:04d}: {entry['text'][:50]} | diff: {', '.join(diff_chars[:3])}")
            found = True
    if not found:
        print('  None found.')

    # === CHECK 15: CHECK 2 で見つかった件の詳細分析 ===
    # vvproj が ROHAN より近いが、拗音潰しがある件を列挙
    print()
    print('=== CHECK 15: 問題なし but vvproj has 拗音/ツァ/フォ等 collapse vs ROHAN (詳細) ===')
    all_collapse_pairs = rare_pairs + youon_pairs
    found = False
    for entry in parsed:
        if '問題なし' not in entry['judge'] or not entry['rohan_norm']:
            continue
        collapses = []
        for rare, collapsed in all_collapse_pairs:
            if rare in entry['rohan_norm'] and rare not in entry['vvproj_norm'] and collapsed in entry['vvproj_norm']:
                collapses.append(f'{rare}→{collapsed}')
        if collapses:
            dist_v = levenshtein_distance(entry['vvproj_norm'], entry['rohan_norm'])
            dist_p = levenshtein_distance(entry['pyojt_norm'], entry['rohan_norm'])
            print(f"  #{entry['num']:04d}: {entry['text'][:50]}")
            print(f"    潰し: {', '.join(collapses)} | 距離: vvproj={dist_v}, pyojt={dist_p}")
            found = True
    if not found:
        print('  None found.')

    print()
    print('=== Verification complete ===')


if __name__ == '__main__':
    main()

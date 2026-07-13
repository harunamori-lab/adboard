#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
広告ボード投稿ジェネレーター（視覚版・確定規格）
================================================
規格（2026-07-14 春菜確定、変更禁止）:
- 広告セットごとのカードに「実際の広告画像（Metaサムネイル）」と「実際のキャプション」を必ず埋め込む
- お金の流れは比率バー、状態は色チップで視覚化
- 平易な言葉。抽象比喩・幼稚な図解は使わない

使い方:
  python3 board_daily.py weekly  → /tmp/board_weekly.json を生成
  python3 board_daily.py daily   → /tmp/board_daily.json を生成
生成後: python3 board_util.py post /tmp/board_daily.json
"""
import json, sys, datetime, calendar, requests
from pathlib import Path

ADBOARD = Path(__file__).resolve().parent
DASH = ADBOARD.parent / 'meta-ads-dashboard'
sys.path.insert(0, str(DASH))
from secrets_helper import get_meta_token

env = {}
for line in (DASH / '.env').read_text().splitlines():
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip().strip('"')
TOKEN = get_meta_token()
ACC = env.get('AD_ACCOUNT_ID', '')
API = 'https://graph.facebook.com/v21.0'
GOAL = 5_000_000
NOW = datetime.datetime.now()
TODAY = NOW.strftime('%Y-%m-%d')
D, DIM = NOW.day, calendar.monthrange(NOW.year, NOW.month)[1]
MONTH_START = f'{NOW.year}-{NOW.month:02d}-01'

def ins(since, until, level='account'):
    fields = 'spend,impressions,clicks,ctr,cpm,frequency,actions,action_values'
    if level == 'adset': fields = 'adset_name,' + fields
    if level == 'ad': fields = 'ad_name,adset_name,' + fields
    p = {'fields': fields, 'time_range': json.dumps({'since': since, 'until': until}),
         'limit': 300, 'access_token': TOKEN}
    if level != 'account': p['level'] = level
    try:
        return requests.get(f'{API}/act_{ACC}/insights', params=p, timeout=45).json().get('data', [])
    except Exception:
        return []

def parse(row):
    am = {x['action_type']: int(float(x['value'])) for x in (row.get('actions') or [])}
    av = {x['action_type']: float(x['value']) for x in (row.get('action_values') or [])}
    sp = float(row.get('spend', 0) or 0)
    return dict(spend=int(sp), ctr=float(row.get('ctr', 0) or 0),
                freq=float(row.get('frequency', 0) or 0),
                cart=am.get('add_to_cart', 0), co=am.get('initiate_checkout', 0),
                purch=am.get('purchase', 0), pv=int(av.get('purchase', 0)),
                lp=am.get('landing_page_view', 0),
                roas=(av.get('purchase', 0) / sp) if sp else 0)

def acct(s, u):
    d = ins(s, u)
    return parse(d[0]) if d else parse({})

def ago(n): return (NOW - datetime.timedelta(days=n)).strftime('%Y-%m-%d')
def yen(n): return f'¥{n:,}'

def active_ads():
    out = []
    r = requests.get(f'{API}/act_{ACC}/ads',
        params={'fields': 'name,effective_status,adset{name},creative{id}',
                'limit': 300, 'access_token': TOKEN,
                'effective_status': '["ACTIVE","IN_PROCESS","PENDING_REVIEW"]'}, timeout=40).json()
    for ad in r.get('data', []):
        cid = (ad.get('creative') or {}).get('id', '')
        thumb, body = '', ''
        if cid:
            cd = requests.get(f'{API}/{cid}',
                params={'fields': 'thumbnail_url,body,object_story_spec,asset_feed_spec',
                        'thumbnail_width': 400, 'thumbnail_height': 400,
                        'access_token': TOKEN}, timeout=30).json()
            thumb = cd.get('thumbnail_url', '') or ''
            body = cd.get('body', '') or (cd.get('object_story_spec') or {}).get('link_data', {}).get('message', '') or ''
            if not body:
                bs = (cd.get('asset_feed_spec') or {}).get('bodies') or []
                body = bs[0].get('text', '') if bs else ''
        out.append(dict(name=ad.get('name', ''), adset=(ad.get('adset') or {}).get('name', ''),
                        status=ad.get('effective_status', ''), thumb=thumb, body=body))
    return out

def chips(m, w):
    c = ''
    if m['pv'] > 0: c += '<span class="bdchip g">売上あり</span>'
    elif m['cart'] >= 5: c += '<span class="bdchip y">カート発生中</span>'
    elif w['ctr'] >= 5: c += '<span class="bdchip y">反応あり</span>'
    else: c += '<span class="bdchip r">まだ静か</span>'
    if w['freq'] >= 2.5: c += '<span class="bdchip r">飽きられ注意</span>'
    elif w['freq'] >= 2.0: c += f'<span class="bdchip y">表示{w["freq"]:.1f}回</span>'
    return c

def set_cards():
    sets_m = {r.get('adset_name', ''): parse(r) for r in ins(MONTH_START, TODAY, 'adset')}
    sets_7 = {r.get('adset_name', ''): parse(r) for r in ins(ago(6), TODAY, 'adset')}
    ads_month = {r.get('ad_name', ''): parse(r) for r in ins(MONTH_START, TODAY, 'ad')}
    ads = active_ads()
    html = ''
    for nm, m in sorted(sets_m.items(), key=lambda x: -x[1]['pv']):
        if m['spend'] < 300: continue
        w = sets_7.get(nm, parse({}))
        rows = ''
        for a in [x for x in ads if x['adset'] == nm]:
            st = ads_month.get(a['name'], {})
            copy1 = (a['body'] or '').split('\n')[0][:34] or '（本文なし）'
            img = f'<img class="bdimg" src="{a["thumb"]}" alt="">' if a['thumb'] else ''
            sold = '<span class="bdchip g">この絵と言葉が売った</span>' if st.get('pv', 0) > 0 else ''
            stat = (f'消化{yen(st.get("spend",0))}・CTR{st.get("ctr",0):.1f}%・カート{st.get("cart",0)}・'
                    f'購入{st.get("purch",0)}・売上{yen(st.get("pv",0))}') if st else 'データ蓄積中'
            rows += (f'<div class="bdrow">{img}<div><div class="bdcopy">「{copy1}…」{sold}</div>'
                     f'<div class="bdstat">{stat}</div></div></div>')
        html += (f'<div class="bdcard"><div class="bdhead"><b>{nm[:36]}</b>{chips(m,w)}</div>'
                 f'<div class="bdstats">今月: 広告費 <b>{yen(m["spend"])}</b>｜売上 <b>{yen(m["pv"])}</b>'
                 f'（{m["roas"]:.1f}倍）｜購入 <b>{m["purch"]}</b>｜カート <b>{m["cart"]}</b></div>{rows}</div>')
    return html

def money_bar(mtd):
    ratio = min(mtd['spend'] / mtd['pv'] * 100, 100) if mtd['pv'] else 100
    return (f'<div class="bdbarrow"><span class="bdbarlabel">広告費</span>'
            f'<span class="bdbar"><span class="bdfill grey" style="width:{ratio:.0f}%"></span>'
            f'<span class="bdval">{yen(mtd["spend"])}</span></span></div>'
            f'<div class="bdbarrow"><span class="bdbarlabel">売上</span>'
            f'<span class="bdbar"><span class="bdfill" style="width:100%"></span>'
            f'<span class="bdval">{yen(mtd["pv"])}</span></span></div>')

def build(mode):
    mtd = acct(MONTH_START, TODAY)
    yesterday = acct(ago(1), ago(1))
    prog = mtd['pv'] / GOAL * 100
    pace = D / DIM * 100
    proj = int(mtd['pv'] / D * DIM) if D else 0
    cards = set_cards()
    if mode == 'weekly':
        payload = {
            'title': f'今週の広告戦略（{NOW.strftime("%-m/%-d")}週・視覚版）',
            'week': f'{NOW.strftime("%-m/%-d")}週',
            'sections': [
                {'id': 's1', 'heading': '今月のお金の流れと目標',
                 'html': money_bar(mtd) + f'<div class="bdbig">広告費の<b>{mtd["roas"]:.1f}倍</b>の売上。'
                         f'目標¥5,000,000に対して<b>{prog:.0f}%</b>（日数は{pace:.0f}%経過）。'
                         f'このままなら月末着地は約{yen(proj)}。</div>'},
                {'id': 's2', 'heading': '広告セット別の成績（実際の画像とキャプション）', 'html': cards},
                {'id': 's3', 'heading': '今週の判定日',
                 'html': ('<table><tr><th>日</th><th>決めること</th></tr>'
                          '<tr><td>7/14</td><td>アメリカテストの停止判定</td></tr>'
                          '<tr><td>7/16</td><td>新設3つ（ASC・複製・緑の画像）の判定。良いものは+30%</td></tr>'
                          '<tr><td>7/18</td><td>🔴 8月在庫の発注締切</td></tr>'
                          '<tr><td>7/19</td><td>フープ・テニブレの継続判定</td></tr></table>')},
                {'id': 's4', 'heading': '相談したいこと（コメントください）',
                 'html': ('①購入手続きまで進んだ人の大半が最後の画面で離脱。サイト側（価格の納得感、送料表示、決済UX）の改善アイデア募集。'
                          '<br>②テニブレは今月広告経由ゼロ。画像を変えるか休ませるか。'
                          '<br>③8月の発注数量、強気か堅実か。')},
            ]}
    else:
        payload = {
            'title': f'デイリーPDCA {NOW.strftime("%-m/%-d")}',
            'week': 'デイリー',
            'sections': [
                {'id': 's1', 'heading': '昨日の結果と現在地',
                 'html': money_bar(mtd) + f'<div class="bdbig">昨日: 消化{yen(yesterday["spend"])}・購入{yesterday["purch"]}件・'
                         f'売上{yen(yesterday["pv"])}・カート{yesterday["cart"]}。月の進捗<b>{prog:.0f}%</b>'
                         f'（日数{pace:.0f}%）、着地予測 約{yen(proj)}。</div>'},
                {'id': 's2', 'heading': '広告セット別（実際の画像つき）', 'html': cards},
                {'id': 's3', 'heading': '今日やること・判定・相談',
                 'html': '（コーチが本日の提案をコメントで追記します。質問はこのスレッドへ）'},
            ]}
    out = Path(f'/tmp/board_{mode}.json')
    out.write_text(json.dumps(payload, ensure_ascii=False))
    print(f'生成: {out}（画像{payload["sections"][1]["html"].count("<img")}枚埋め込み）')

if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else 'daily')

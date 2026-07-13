#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
広告ボード操作ユーティリティ（毎朝コーチ・手動運用の共通ツール）
================================================================
使い方:
  python3 board_util.py post <json>            投稿する
  python3 board_util.py comments <時間>         直近N時間のコメント一覧（JSON出力）
  python3 board_util.py reply <post_id> <section_id> "<本文>"
                                                コーチ（AI）名義でスレッドに返信
  python3 board_util.py latest                  最新投稿のIDとセクション一覧
"""
import json, re, sys, datetime, requests
from pathlib import Path

BASE = Path(__file__).resolve().parent
SB_URL = 'https://mlxndtqftmkwwpfyvbhg.supabase.co'
AUTHOR_AI = 'コーチ（AI）'

def anon_key():
    return 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1seG5kdHFmdG1rd3dwZnl2YmhnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODM5Njc0NTUsImV4cCI6MjA5OTU0MzQ1NX0.R_tMOYbkTKQUTRs-77z56GrD62lqeBy9GThf9NfWFh4'

def hdr():
    k = anon_key()
    return {'apikey': k, 'Authorization': f'Bearer {k}', 'Content-Type': 'application/json'}

def post(path_json):
    payload = json.loads(Path(path_json).read_text())
    r = requests.post(f'{SB_URL}/rest/v1/board_posts',
                      headers={**hdr(), 'Prefer': 'return=representation'},
                      json=payload, timeout=30)
    if r.status_code in (200, 201):
        pid = r.json()[0]['id']
        print(f'投稿完了: {payload["title"]} (id={pid})')
        return 0
    print(f'失敗 {r.status_code}: {r.text[:200]}')
    return 1

def comments(hours):
    since = (datetime.datetime.utcnow() - datetime.timedelta(hours=float(hours))).isoformat() + 'Z'
    r = requests.get(f'{SB_URL}/rest/v1/board_comments',
                     headers=hdr(),
                     params={'created_at': f'gte.{since}', 'order': 'created_at.asc',
                             'select': 'post_id,section_id,author,body,created_at'},
                     timeout=30)
    rows = [c for c in r.json() if c.get('author') != AUTHOR_AI] if r.status_code == 200 else []
    print(json.dumps(rows, ensure_ascii=False, indent=1))
    return 0

def reply(post_id, section_id, body):
    r = requests.post(f'{SB_URL}/rest/v1/board_comments', headers=hdr(),
                      json={'post_id': post_id, 'section_id': section_id,
                            'author': AUTHOR_AI, 'body': body}, timeout=30)
    print('返信完了' if r.status_code in (200, 201) else f'失敗 {r.status_code}: {r.text[:150]}')
    return 0 if r.status_code in (200, 201) else 1

def latest():
    r = requests.get(f'{SB_URL}/rest/v1/board_posts', headers=hdr(),
                     params={'order': 'created_at.desc', 'limit': 1,
                             'select': 'id,title,week,sections'}, timeout=30)
    if r.status_code == 200 and r.json():
        p = r.json()[0]
        print(json.dumps({'id': p['id'], 'title': p['title'],
                          'sections': [{'id': s['id'], 'heading': s['heading']} for s in p['sections']]},
                         ensure_ascii=False, indent=1))
    else:
        print('{}')
    return 0

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'post': sys.exit(post(sys.argv[2]))
    if cmd == 'comments': sys.exit(comments(sys.argv[2] if len(sys.argv) > 2 else 24))
    if cmd == 'reply': sys.exit(reply(sys.argv[2], sys.argv[3], sys.argv[4]))
    if cmd == 'latest': sys.exit(latest())
    print(__doc__)

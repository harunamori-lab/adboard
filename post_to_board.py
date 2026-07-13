#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
広告ボードへの投稿スクリプト
============================
使い方:
  python3 post_to_board.py week1.json   # JSONファイルの内容を投稿
JSON形式: {"title": "...", "week": "...", "sections": [{"id":"s1","heading":"...","html":"..."}]}
"""
import json, re, sys, requests
from pathlib import Path

BASE = Path(__file__).resolve().parent
SB_URL = 'https://mlxndtqftmkwwpfyvbhg.supabase.co'

def anon_key():
    return 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1seG5kdHFmdG1rd3dwZnl2YmhnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODM5Njc0NTUsImV4cCI6MjA5OTU0MzQ1NX0.R_tMOYbkTKQUTRs-77z56GrD62lqeBy9GThf9NfWFh4'

def post(payload):
    key = anon_key()
    r = requests.post(f'{SB_URL}/rest/v1/board_posts',
        headers={'apikey': key, 'Authorization': f'Bearer {key}',
                 'Content-Type': 'application/json', 'Prefer': 'return=representation'},
        json=payload, timeout=30)
    if r.status_code in (200, 201):
        print(f'投稿完了: {payload["title"]}')
        return True
    print(f'失敗 {r.status_code}: {r.text[:200]}')
    return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('使い方: python3 post_to_board.py <投稿JSON>')
        sys.exit(1)
    payload = json.loads(Path(sys.argv[1]).read_text())
    sys.exit(0 if post(payload) else 1)

#!/usr/bin/env python
# coding: utf-8

import MySQLdb  # MySQL-python
from collections import defaultdict
from time import sleep

def connect():
    # 設定ファイル等から読み込む.
    host = 'dbhost'
    user = 'sampleuser'
    passwd = 'samplesecret'
    db = 'sampledb'
    return MySQLdb.connect(host=host, user=user, passwd=passwd, db=db)

def gather_infos(con):
    con.query('show full processlist')
    for row in con.store_result().fetch_row(maxrows=100, how=1):
        if row['Info']:
            yield row['Info']

def main():
    con = connect()
    # Python 2.7 では Counter を使うともっとシンプルに書ける.
    dic = defaultdict(int)

    while True:
        for row in gather_infos(con):
            if row == 'show full processlist':
                continue
            # ざっくりと、変数ぽい部分をカット
            for k in ('=', ' IN ', ' BETWEEN '):
                row = row.split(k)[0]
                row = row.split(k.lower())[0]
            dic[row] += 1

        items = dic.items()
        items.sort(key=lambda x: x[1], reverse=True)
        print '--'
        for it in items[:20]:
            print it[1], it[0]

        sleep(1)

if __name__ == '__main__':
    main()
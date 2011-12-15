#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function

import os
import sys
import re
from time import sleep
from collections import defaultdict
from ConfigParser import SafeConfigParser
from optparse import OptionParser

import MySQLdb  # MySQL-python
#import pymysql as MySQLdb  # PyMySQL


CMD_PROCESSLIST = "show full processlist"


def connect(conf='~/.my.cnf', section='DEFAULT'):
    u"""
    ~/.my.cnf から接続に必要な情報を読み込む.
    """
    #parser = SafeConfigParser(allow_no_value=True)
    parser = SafeConfigParser()
    parser.read([os.path.expanduser(conf)])

    host = parser.get(section, 'host')
    user = parser.get(section, 'user')
    password = parser.get(section, 'password')
    #port = parser.getint(section, 'port')
    #return MySQLdb.connect(host=host, user=user, passwd=password, port=port)
    return MySQLdb.connect(host=host, user=user, passwd=password)


def gather_infos(con):
    con.query(CMD_PROCESSLIST)
    for row in con.store_result().fetch_row(maxrows=200, how=1):
        if row['Info']:
            yield row['Info']


def normalize_query(row):
    u"""
    クエリを種類ごとに集計するために変形する.
    """
    row = ' '.join(row.split())
    subs = [
            (r"\b\d+\b", "N"),
            (r"\b0x[0-9A-Fa-f]+\b", "0xN"),
            (r"(\\')", ''),
            (r'(\\")', ''),
            (r"'[^']+'", "'S'"),
            (r'"[^"]+"', '"S"'),
            (r'(([NS],){4,})', r'...'),
            ]
    for pat,sub in subs:
        row = re.sub(pat, sub, row)
    return row


def build_option_parser():
    parser = OptionParser()
    parser.add_option(
            '-o', '--out',
            help="write raw queries to this file."
            )
    parser.add_option(
            '-c', '--config',
            help="read MySQL configuration instead of ~/.my.cnf",
            default='~/.my.cnf'
            )
    parser.add_option(
            '-s', '--section',
            help="read MySQL configuration from this section.",
            default="DEFAULT"
            )
    parser.add_option(
            '-n', '--num-summary', metavar="K",
            help="show most K common queries.",
            type="int", default=10
            )
    return parser


def main():
    opts, args = build_option_parser().parse_args()

    outfile = None
    if opts.out:
        outfile = open(opts.out, "w")

    con = connect(opts.config, opts.section)

    counter = defaultdict(int)
    while True:
        for row in gather_infos(con):
            if row == CMD_PROCESSLIST:
                continue
            counter[normalize_query(row)] += 1
            if outfile:
                print(row, file=outfile)

        print('---')
        items = counter.items()
        items.sort(key=lambda x: x[1], reverse=True)
        for query, count in items[:opts.num_summary]:
            print("{1:4d} {2}".format(count, query))
        print()
        sleep(1)


if __name__ == '__main__':
    main()
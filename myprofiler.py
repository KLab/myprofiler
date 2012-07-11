#!/usr/bin/env python
# coding: utf-8

"""myprofiler - Casual MySQL Profiler

https://github.com/KLab/myprofiler
"""

import os
import sys
import re
from time import sleep
from collections import defaultdict
from ConfigParser import SafeConfigParser
from optparse import OptionParser

try:
    import MySQLdb  # MySQL-python
    from MySQLdb.cursors import DictCursor
except ImportError:
    try:
        import pymysql as MySQLdb  # PyMySQL
        from pymysql.cursors import DictCursor
    except ImportError:
        print "Please install MySQLdb or PyMySQL"
        sys.exit(1)


CMD_PROCESSLIST = "show full processlist"


def connect(cnf):
    args = {}
    args['host'] = cnf.get('host', 'localhost')
    args['user'] = cnf.get('user', '')
    args['passwd'] = cnf.get('password', '')
    args['charset'] = cnf.get('default-character-set', 'utf8')
    if 'port' in cnf:
        args['port'] = int(get('port'))
    return MySQLdb.connect(**args)


def processlist(con):
    cur = con.cursor(DictCursor)
    cur.execute(CMD_PROCESSLIST)
    for row in cur.fetchall():
        if row['Info']:
            yield row['Info']


def normalize_query(row):
    """
    Modify query to summarize.
    """
    row = ' '.join(row.split())
    subs = [
            (r"[+\-]{0,1}\b\d+\b", "N"),
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


def read_mycnf(extra_file=None, group_suffix=''):
    cnf_files = [os.path.expanduser('~/.my.cnf')]
    if extra_file is not None:
        if not os.path.isfile(extra_file):
            print >>sys.stderr, "[warn]", extra_file, "is not exists."
        else:
            cnf_files += [extra_file]

    parser = SafeConfigParser()
    parser.read(cnf_files)

    cnf = dict(parser.items('client'))
    if group_suffix:
        cnf.update(parser.items('client' + group_suffix))
    return cnf


def build_option_parser():
    parser = OptionParser(add_help_option=False)
    parser.add_option(
            '-o', '--out',
            help="Write raw queries to this file.",
            )
    parser.add_option(
            '-e', '--defaults-extra-file', dest='extra_file',
            help="Read MySQL configuration from this file additionaly",
            )
    parser.add_option(
            '-s', '--defaults-group-suffix', dest='group_suffix',
            help="Read MySQL configuration from this section additionally",
            )
    parser.add_option(
            '-n', '--num-summary', metavar="K",
            help="show most K common queries. (default: 10)",
            type="int", default=10
            )
    parser.add_option(
            '-i', '--interval',
            help="Interval of executing show processlist [sec] (default: 1.0)",
            type="float", default=1.0
            )
    parser.add_option('-u', '--user')
    parser.add_option('-p', '--password')
    parser.add_option('-h', '--host')
    parser.add_option('-?', '--help',action="store_true", help="show this message")
    return parser


def show_summary(counter, limit, file=sys.stdout):
    print >>file, '---'
    items = counter.items()
    items.sort(key=lambda x: x[1], reverse=True)
    for query, count in items[:limit]:
        print >>file, "%4d %s" % (count, query)


def main():
    parser = build_option_parser()
    opts, args = parser.parse_args()
    outfile = None

    if opts.help:
        parser.print_help()
        return

    try:
        cnf = read_mycnf(opts.extra_file, opts.group_suffix)
        if opts.user:
            cnf['user'] = opts.user
        if opts.password:
            cnf['password'] = opts.password
        if opts.host:
            cnf['host'] = opts.host
        con = connect(cnf)

        if opts.out:
            outfile = open(opts.out, "w")
    except Exception, e:
        parser.error(e)

    counter = defaultdict(int)
    try:
        while True:
            for row in processlist(con):
                if row == CMD_PROCESSLIST:
                    continue
                counter[normalize_query(row)] += 1
                if outfile:
                    print >>outfile, row

            show_summary(counter, opts.num_summary)
            print
            sleep(opts.interval)
    finally:
        if outfile:
            print >>outfile, "\nSummary"
            show_summary(counter, opts.num_summary, outfile)
            outfile.close()


if __name__ == '__main__':
    main()

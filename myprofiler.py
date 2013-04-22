#!/usr/bin/env python
# coding: utf-8

"""myprofiler - Casual MySQL Profiler

https://github.com/KLab/myprofiler
"""

import os
import sys
import re
from time import sleep
from collections import defaultdict, deque
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


class NoValueConfigParser(SafeConfigParser):
    """
    ConfigParser accepts no value.
    """
    OPTCRE = re.compile(
        r'(?P<option>[^:=\s][^:=]*)'          # very permissive!
        r'\s*'                                # any number of space/tab,
        r'(?P<vi>[:=]?)\s*'                   # optionally followed by
                                              # separator (either : or
                                              # =), followed by any #
                                              # space/tab
        r'(?P<value>.*)$'                     # everything up to eol
        )


class SummingCollector(object):
    def __init__(self):
        self.sums = defaultdict(int)

    def turn(self):
        pass

    def append(self, item):
        self.sums[item] += 1

    def summary(self):
        items = [(k, v) for k, v in self.sums.items() if v > 0]
        items.sort(key=lambda x: x[1], reverse=True)
        return items

class CappedCollector(SummingCollector):
    def __init__(self, cap):
        self._queue = deque([defaultdict(int) for _ in range(cap)])
        SummingCollector.__init__(self)

    def append(self, item):
        self._queue[-1][item] += 1
        SummingCollector.append(self, item)

    def turn(self):
        self._queue.append(defaultdict(int))
        dropped = self._queue.popleft()
        for k, v in dropped.items():
            self.sums[k] -= v


CMD_PROCESSLIST = "show full processlist"


def connect(cnf):
    args = {}
    args['host'] = cnf.get('host', 'localhost')
    args['user'] = cnf.get('user', '')
    args['passwd'] = cnf.get('password', '')
    args['charset'] = cnf.get('default-character-set', 'utf8')
    if 'port' in cnf:
        args['port'] = int(cnf.get('port'))
    return MySQLdb.connect(**args)


def processlist(con):
    cur = con.cursor(DictCursor)
    cur.execute(CMD_PROCESSLIST)
    for row in cur.fetchall():
        query = row['Info']
        if query and query != CMD_PROCESSLIST:
            yield query


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
    cnf_files = ['/etc/my.cnf']
    if extra_file is not None:
        if not os.path.isfile(extra_file):
            print >>sys.stderr, "[warn]", extra_file, "is not exists."
        else:
            cnf_files += [extra_file]
    cnf_files += ['~/.my.cnf']
    cnf_files = map(os.path.expanduser, cnf_files)

    parser = NoValueConfigParser()
    parser.read(cnf_files)

    try:
        cnf = dict(parser.items('client'))
    except Exception:
        cnf = {}
    if group_suffix:
        try:
            cnf.update(parser.items('client' + group_suffix))
        except Exception:
            pass
    return cnf


def build_option_parser():
    parser = OptionParser(add_help_option=False)
    option = parser.add_option
    option('-o', '--out',
           help="Write raw queries to this file.",
           )
    option('-e', '--defaults-extra-file', dest='extra_file',
           help="Read MySQL configuration from this file additionaly",
           )
    option('-s', '--defaults-group-suffix', dest='group_suffix',
           help="Read MySQL configuration from this section additionally",
           )
    option('-n', '--num-summary', metavar="K",
           help="show most K common queries. (default: %default)",
           type="int", default=10
           )
    option('-l', '--limit', metavar="L",
           help="Summarize most recent L results. "
                "0 means all queries since start are summarized (default).",
           type="int", default=0
           )
    option('-i', '--interval',
           help="Interval of executing show processlist [sec] (default: %default)",
           type="float", default=1.0
           )
    option('-u', '--user')
    option('-p', '--password')
    option('-h', '--host')
    option('-?', '--help', action="store_true", help="show this message")
    return parser


def show_summary(collector, num_summary, file=sys.stdout):
    print >>file, '-'*20
    summary = collector.summary()
    for query, count in summary[:num_summary]:
        print >>file, "%4d %s" % (count, query)
    print >>file
    file.flush()


def profile(con, num_summary, limit, interval=1.0, outfile=None):
    if limit:
        collector = CappedCollector(limit)
    else:
        collector = SummingCollector()

    try:
        while True:
            for query in processlist(con):
                collector.append(normalize_query(query))
                if outfile:
                    print >>outfile, query
            show_summary(collector, num_summary)
            sleep(interval)
            collector.turn()
    finally:
        if outfile:
            print >>outfile, "\nSummary"
            show_summary(counter, num_summary, outfile)
            outfile.close()


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

    profile(con, opts.num_summary, opts.limit, opts.interval, outfile)


if __name__ == '__main__':
    main()

# myprofiler

myprofiler is statistical profiler for MySQL.

It watches `SHOW FULL PROCESSLIST` periodically, and count each query.

## Install

Download archive and put it on directory in your PATH.

```console
wget https://github.com/KLab/myprofiler/releases/download/0.1/myprofiler.linux_amd64.tar.gz
tar xf myprofiler.linux_amd64.tar.gz
mv myprofiler ~/bin
```

## Options

```console
$ ./myprofiler -h
Usage of ./myprofiler:
  -dump="": Write raw queries to this file
  -host="localhost": Host of database
  -interval=1: (float) Interval of executing show processlist
  -limit=0: Limit how many recent samples are summarized
  -password="": Password
  -port=3306: Port
  -summary=10: How most common queries are shown
  -user="": User
```


## Profiling

```console
myprofiler -host=db1234 -user=dbuser -password=dbpass -interval=0.2 -summary=30
```

You should use user having 'PROCESS' privilege, or same user to your app.
See [document](https://dev.mysql.com/doc/refman/5.6/en/show-processlist.html) for
"SHOW FULL PROCESSLIST".

myprofiler sleeps seconds specified by `-interval` for each sample.
0.2 (up to 5 queries/sec) may be low enough for your production DB.

myprofiler transform query like mysqldumpslow. For example, "SELECT * FROM user WHERE id=42"
is transformed into "SELECT * FROM user WHERE id=N".
myprofiler counts transformed quries and show top N (specified by `-summary`) queries.

You can get raw query by `-dump=query.txt` option. It is useful when you want to EXPLAIN
heavy queries.


## Monitoring (long profiling)

You can use log rotation tool like rotatelogs or multilog.


```console
myprofiler -host=db1234 -user=dbuser -password=dbpass -limit=60 | rotatelogs logs/myprofiler.%Y%m%d 86400
```

`-limit=60` means myprofiler only count last 60 samples.
Since interval is 1sec (default), this command shows top queries in last minute.

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
Usage of ./myprofiler:
  -delay=1: (int) Show summary for each `delay` samples. -interval=0.1 -delay=30 shows summary for every 3sec
  -dump="": Write raw queries to this file
  -host="localhost": Host of database
  -interval=1: (float) Sampling interval
  -password="": Password
  -port=3306: Port
  -last=0: (int) Last N samples are summarized. 0 means summarize all samples
  -top=10: (int) Show N most common queries
  -user="": User
```


## Profiling

```console
myprofiler -host=db1234 -user=dbuser -password=dbpass -interval=0.2 -delay=10 -top=30
```

You should use user having 'PROCESS' privilege, or same user to your app.
See [document](https://dev.mysql.com/doc/refman/5.6/en/show-processlist.html) for
"SHOW FULL PROCESSLIST".

myprofiler transform query like mysqldumpslow. For example, "SELECT * FROM user WHERE id=42"
is transformed into "SELECT * FROM user WHERE id=N".
myprofiler counts transformed quries and show top N (specified by `-top`) queries.

myprofiler sleeps seconds specified by `-interval` for each sample.
0.2 (up to 5 queries/sec) may be low enough for your production DB.

You can get raw query by `-dump=rawquery.txt` option. It is useful when you want to EXPLAIN
heavy queries.


## Monitoring (long profiling)

You can use log rotation tool like rotatelogs or multilog.


```console
myprofiler -host=db1234 -user=dbuser -password=dbpass -last=60 -delay=30 | rotatelogs logs/myprofiler.%Y%m%d 86400
```

`-last=60` means myprofiler only summarize last 60 samples.
Since interval is 1 sec by default, this command shows top queries in minute.

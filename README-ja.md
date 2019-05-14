# myprofiler

myprofiler は MySQL のサンプリングプロファイラです。

"SHOW FULL PROCESSLIST" クエリを定期的に実行して、クエリをカウントします。

## インストール

tarball をダウンロードして展開し、実行ファイルを PATH が通ったディレクトリに配置します。

```console
wget https://github.com/KLab/myprofiler/releases/download/0.2/myprofiler.linux_amd64.tar.gz
tar xf myprofiler.linux_amd64.tar.gz
mv myprofiler ~/bin
```

## 起動オプション

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


## 短期間のプロファイリング

いま目の前でなにかパフォーマンスの問題が起こってる場合、次のようにして利用すると良いでしょう。

```console
myprofiler -host=db1234 -user=dbuser -password=dbpass -interval=0.2 -delay=10 -top=30
```

user は 'PROCESS' 権限を持っているユーザーか、アプリが利用しているのと同じユーザーを使ってください。
"SHOW FULL PROCESSLIST" の制限については [ドキュメント](https://dev.mysql.com/doc/refman/5.6/en/show-processlist.html)
を参照してください。

myprofiler はサンプリングしたクエリを mysqldumpslow のように変換します。
例えば、"SELECT * FROM user WHERE id=42" というクエリは "SELECT * FROM user WHERE id=N" に変換されます。
変換したクエリをカウントし、上位 N (`-top` オプションで指定する) 個のクエリを表示します。

myprofiler はサンプリングの間に `-interval` で指定された秒数だけ sleep します。
0.2 (5クエリ/秒以下) は、本番の MySQL サーバーを邪魔しない、十分低い値でしょう。
`-delay=10` を指定しているので、サマリは2秒に1回表示されます。

EXPLAIN でクエリを調査したいなどの理由で生のクエリが欲しい場合、 `-dump=rawquery.txt` オプションを利用できます。


## 長期間のプロファイリング (モニタリング)

まれに問題が起こり、その場でプロファイリングを実行できない場合は、
rotatelogs や multilog といったツールと組み合わせて長期間プロファイリングしつづける事ができます。


```console
myprofiler -host=db1234 -user=dbuser -password=dbpass -last=60 -delay=30 | rotatelogs logs/myprofiler.%Y%m%d 86400
```

`-last=60` は、最近60回のサンプルだけをカウントするという意味です。
interval のデフォルト値は1秒なので、各サマリは1分間の統計を表示することになります。

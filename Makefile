release:
	GOOS=linux go build myprofiler.go
	tar cvzf myprofiler.linux_amd64.tar.gz myprofiler
	GOOS=darwin go build myprofiler.go
	tar cvzf myprofiler.darwin_amd64.tar.gz myprofiler

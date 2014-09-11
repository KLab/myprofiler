package main

import (
	"database/sql"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"os/user"
	"regexp"
	"sort"
	"strings"
	"time"

	_ "github.com/go-sql-driver/mysql"
)

type Config struct {
	dump       io.Writer
	numSummary int
	limit      int
	interval   float64
}

type NormalizePattern struct {
	re   *regexp.Regexp
	subs string
}

func (p *NormalizePattern) Normalize(q string) string {
	return p.re.ReplaceAllString(q, p.subs)
}

var (
	normalizePatterns []NormalizePattern = []NormalizePattern{
		NormalizePattern{regexp.MustCompile(`[+\-]{0,1}\b\d+\b`), "N"},
		NormalizePattern{regexp.MustCompile(`\b0x[0-9A-Fa-f]+\b`), "0xN"},
		NormalizePattern{regexp.MustCompile(`(\\')`), ""},
		NormalizePattern{regexp.MustCompile(`(\\")`), ""},
		NormalizePattern{regexp.MustCompile(`'[^']+'`), "S"},
		NormalizePattern{regexp.MustCompile(`"[^"]+"`), "S"},
		NormalizePattern{regexp.MustCompile(`(([NS]\s*,\s*){4,})`), "..."},
	}
)

func processList(db *sql.DB) []string {
	procList := "SHOW FULL PROCESSLIST"
	rows, err := db.Query(procList)

	queries := []string{}

	if err != nil {
		log.Println(err)
		return queries
	}

	for rows.Next() {
		var user, host, db, command, state, info string
		var id, time int
		rows.Scan(&id, &user, &host, &db, &command, &time, &state, &info)
		if info != "" && info != procList {
			queries = append(queries, info)
		}
	}
	rows.Close()
	return queries
}

func normalizeQuery(query string) string {
	parts := strings.Split(query, " ")
	query = strings.Join(parts, " ")
	for _, pat := range normalizePatterns {
		query = pat.Normalize(query)
	}
	return query
}

type pair struct {
	q string
	c int64
}
type pairList []pair

func (pl pairList) Len() int {
	return len(pl)
}

func (pl pairList) Less(i, j int) bool {
	return pl[i].c > pl[j].c
}

func (pl pairList) Swap(i, j int) {
	pl[i], pl[j] = pl[j], pl[i]
}

func showSummary(sum map[string]int64, n int) {
	counts := []pair{}
	for q, c := range sum {
		counts = append(counts, pair{q, c})
	}
	sort.Sort(pairList(counts))

	fmt.Println("## ", time.Now().Local())
	for i, p := range counts {
		if i >= n {
			break
		}
		fmt.Printf("%4d %s\n", p.c, p.q)
	}
}

func profile(db *sql.DB, cfg *Config) {
	count := make(map[string]int64)
	for {
		queries := processList(db)
		for _, q := range queries {
			q = normalizeQuery(q)
			count[q]++
		}
		showSummary(count, cfg.numSummary)
		time.Sleep(time.Duration(float64(time.Second) * cfg.interval))
	}
}

func main() {
	var host, dbuser, password, dumpfile string
	var port int

	currentUser, err := user.Current()
	if err != nil {
		dbuser = ""
	} else {
		dbuser = currentUser.Name
	}
	cfg := Config{}
	flag.StringVar(&host, "host", "localhost", "Host of database. or Unix socket path")
	flag.StringVar(&dbuser, "user", dbuser, "user")
	flag.StringVar(&password, "password", "", "Password")
	flag.IntVar(&port, "port", 3306, "port")
	flag.StringVar(&dumpfile, "dump", "", "Write raw queries to this file")
	flag.IntVar(&cfg.numSummary, "summary", 10, "How many most common queries.")
	flag.IntVar(&cfg.limit, "limit", 0, "Limit how many recent queries are summarised.")
	flag.Float64Var(&cfg.interval, "interval", 1.0, "Interval of executing show processlist")
	flag.Parse()

	dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/", dbuser, password, host, port)
	db, err := sql.Open("mysql", dsn)
	if err != nil {
		fmt.Println("dsn: ", dsn)
		log.Fatal(err)
	}

	if dumpfile != "" {
		file, err := os.Create(dumpfile)
		if err != nil {
			log.Fatal(err)
		}
		cfg.dump = file
	}
	profile(db, &cfg)
}

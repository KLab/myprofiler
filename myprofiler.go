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
	"time"

	_ "github.com/go-sql-driver/mysql"
)

type Config struct {
	dump     io.Writer
	topN     int
	last     int
	interval float64
	delay    int
}

type NormalizePattern struct {
	re   *regexp.Regexp
	subs string
}

func (p *NormalizePattern) Normalize(q string) string {
	return p.re.ReplaceAllString(q, p.subs)
}

var normalizePatterns = []NormalizePattern{
	NormalizePattern{regexp.MustCompile(` +`), " "},
	NormalizePattern{regexp.MustCompile(`[+\-]{0,1}\b\d+\b`), "N"},
	NormalizePattern{regexp.MustCompile(`\b0x[0-9A-Fa-f]+\b`), "0xN"},
	NormalizePattern{regexp.MustCompile(`(\\')`), ""},
	NormalizePattern{regexp.MustCompile(`(\\")`), ""},
	NormalizePattern{regexp.MustCompile(`'[^']+'`), "S"},
	NormalizePattern{regexp.MustCompile(`"[^"]+"`), "S"},
	NormalizePattern{regexp.MustCompile(`(([NS]\s*,\s*){4,})`), "..."},
}

func processList(db *sql.DB) []string {
	procList := "SHOW FULL PROCESSLIST"
	rows, err := db.Query(procList)

	queries := []string{}

	if err != nil {
		log.Println(err)
		return queries
	}
	defer rows.Close()

	for rows.Next() {
		var user, host, db, command, state, info *string
		var id, time int
		err := rows.Scan(&id, &user, &host, &db, &command, &time, &state, &info)
		if err != nil {
			log.Print(err)
			continue
		}
		if info != nil && *info != "" && *info != procList {
			queries = append(queries, *info)
		}
	}
	return queries
}

func normalizeQuery(query string) string {
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

type Summarizer interface {
	Update(queries []string)
	Show(out io.Writer, num int)
}

func showSummary(w io.Writer, sum map[string]int64, n int) {
	counts := make([]pair, 0, len(sum))
	for q, c := range sum {
		counts = append(counts, pair{q, c})
	}
	sort.Sort(pairList(counts))

	for i, p := range counts {
		if i >= n {
			break
		}
		fmt.Fprintf(w, "%4d %s\n", p.c, p.q)
	}
}

type summarizer struct {
	counts map[string]int64
}

func (s *summarizer) Update(queries []string) {
	if s.counts == nil {
		s.counts = make(map[string]int64)
	}
	for _, q := range queries {
		s.counts[q]++
	}
}

func (s *summarizer) Show(out io.Writer, num int) {
	showSummary(out, s.counts, num)
}

type recentSummarizer struct {
	last    int
	queries [][]string
}

func (s *recentSummarizer) Update(queries []string) {
	if len(s.queries) >= s.last {
		s.queries = s.queries[1:]
	}
	s.queries = append(s.queries, queries)
}

func (s *recentSummarizer) Show(out io.Writer, num int) {
	counts := make(map[string]int64)
	for _, qs := range s.queries {
		for _, q := range qs {
			counts[q]++
		}
	}
	showSummary(out, counts, num)
}

func NewSummarizer(last int) Summarizer {
	if last > 0 {
		return &recentSummarizer{last: last}
	}
	return &summarizer{make(map[string]int64)}
}

func profile(db *sql.DB, cfg *Config) {
	summ := NewSummarizer(cfg.last)
	cnt := 0
	for {
		queries := processList(db)
		if cfg.dump != nil {
			for _, q := range queries {
				cfg.dump.Write([]byte(q))
				cfg.dump.Write([]byte{'\n'})
			}
		}

		for i, q := range queries {
			queries[i] = normalizeQuery(q)
		}
		summ.Update(queries)

		cnt++
		if cnt >= cfg.delay {
			cnt = 0
			fmt.Println("## ", time.Now().Local().Format("2006-01-02 15:04:05.00 -0700"))
			summ.Show(os.Stdout, cfg.topN)
		}

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
	flag.StringVar(&host, "host", "localhost", "Host of database")
	flag.StringVar(&dbuser, "user", dbuser, "User")
	flag.StringVar(&password, "password", "", "Password")
	flag.IntVar(&port, "port", 3306, "Port")

	flag.StringVar(&dumpfile, "dump", "", "Write raw queries to this file")

	flag.IntVar(&cfg.topN, "top", 10, "(int) Show N most common queries")
	flag.IntVar(&cfg.last, "last", 0, "(int) Last N samples are summarized. 0 means summarize all samples")
	flag.Float64Var(&cfg.interval, "interval", 1.0, "(float) Sampling interval")
	flag.IntVar(&cfg.delay, "delay", 1, "(int) Show summary for each `delay` samples. -interval=0.1 -delay=30 shows summary for every 3sec")

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

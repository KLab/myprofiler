package main

import (
	"testing"
)

func TestNormalize(t *testing.T) {
	var data = []struct{ input, expected string }{
		{"IN ('a', 'b', 'c')", "IN (S, S, S)"},
		{"IN ('a', 'b', 'c', 'd', 'e')", "IN (...S)"},
		{"IN (1, 2, 3)", "IN (N, N, N)"},
		{"IN (1, 2, 3, 4, 5)", "IN (...N)"},
	}

	for _, d := range data {
		if a := normalizeQuery(d.input); a != d.expected {
			t.Errorf("data=%v, actual=%q", d, a)
		}
	}
}

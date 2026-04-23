package cli

import (
	"fmt"
	"strings"
)

var (
	version = "dev"
	commit  = "unknown"
	date    = ""
)

func renderVersion() string {
	lines := []string{fmt.Sprintf("version: %s", strings.TrimSpace(version))}
	if trimmedCommit := strings.TrimSpace(commit); trimmedCommit != "" {
		lines = append(lines, fmt.Sprintf("commit: %s", trimmedCommit))
	}
	if trimmedDate := strings.TrimSpace(date); trimmedDate != "" {
		lines = append(lines, fmt.Sprintf("built: %s", trimmedDate))
	}
	return strings.Join(lines, "\n")
}

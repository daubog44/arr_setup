package cli

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

func isWorkspaceRoot(path string) bool {
	return fileExists(filepath.Join(path, "Taskfile.yml")) && fileExists(filepath.Join(path, "go.mod"))
}

func resolveWorkspaceRoot(override string) (string, error) {
	if strings.TrimSpace(override) == "" {
		return repoRoot()
	}
	absolute, err := filepath.Abs(filepath.Clean(override))
	if err != nil {
		return "", fmt.Errorf("resolve workspace path %q: %w", override, err)
	}
	if !isWorkspaceRoot(absolute) {
		return "", fmt.Errorf("%s is not an initialized HaaC workspace", absolute)
	}
	return absolute, nil
}

func resolveTargetPath(target string) (string, error) {
	if strings.TrimSpace(target) == "" {
		target = "."
	}
	absolute, err := filepath.Abs(filepath.Clean(target))
	if err != nil {
		return "", fmt.Errorf("resolve target path %q: %w", target, err)
	}
	return absolute, nil
}

func directoryEmpty(path string) (bool, error) {
	entries, err := os.ReadDir(path)
	if err != nil {
		return false, err
	}
	return len(entries) == 0, nil
}

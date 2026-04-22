package cli

import (
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
)

type bridge struct {
	repoRoot string
}

func newBridge() (*bridge, error) {
	root, err := repoRoot()
	if err != nil {
		return nil, err
	}
	return &bridge{repoRoot: root}, nil
}

func repoRoot() (string, error) {
	cwd, err := os.Getwd()
	if err != nil {
		return "", fmt.Errorf("resolve working directory: %w", err)
	}
	for current := cwd; ; current = filepath.Dir(current) {
		taskfile := filepath.Join(current, "Taskfile.yml")
		goMod := filepath.Join(current, "go.mod")
		if fileExists(taskfile) && fileExists(goMod) {
			return current, nil
		}
		parent := filepath.Dir(current)
		if parent == current {
			break
		}
	}
	return "", errors.New("could not locate repo root from current working directory")
}

func fileExists(path string) bool {
	info, err := os.Stat(path)
	return err == nil && !info.IsDir()
}

func (b *bridge) runTask(args []string) error {
	taskBinary, err := b.taskBinary()
	if err != nil {
		return err
	}
	env := os.Environ()
	localTaskDir := filepath.Dir(taskBinary)
	env = upsertEnv(env, "PATH", prependPath(localTaskDir, os.Getenv("PATH")))
	return b.run(taskBinary, args, env)
}

func (b *bridge) runTaskWithExtraEnv(args []string, overrides map[string]string) error {
	taskBinary, err := b.taskBinary()
	if err != nil {
		return err
	}
	env := os.Environ()
	localTaskDir := filepath.Dir(taskBinary)
	env = upsertEnv(env, "PATH", prependPath(localTaskDir, os.Getenv("PATH")))
	for key, value := range overrides {
		env = upsertEnv(env, key, value)
	}
	return b.run(taskBinary, args, env)
}

func (b *bridge) run(binary string, args []string, env []string) error {
	cmd := exec.Command(binary, args...)
	cmd.Dir = b.repoRoot
	cmd.Env = env
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin
	if err := cmd.Run(); err != nil {
		var exitErr *exec.ExitError
		if errors.As(err, &exitErr) {
			return fmt.Errorf("command failed with exit code %d", exitErr.ExitCode())
		}
		return err
	}
	return nil
}

func (b *bridge) taskBinary() (string, error) {
	localBinary := filepath.Join(b.repoRoot, ".tools", fmt.Sprintf("%s-%s", runtime.GOOS, runtime.GOARCH), "bin", taskBinaryName())
	if fileExists(localBinary) {
		return localBinary, nil
	}
	return "", fmt.Errorf("repo-local task binary not found at %s; run install-tools or use task directly", localBinary)
}

func taskBinaryName() string {
	if runtime.GOOS == "windows" {
		return "task.exe"
	}
	return "task"
}

func prependPath(first, current string) string {
	if current == "" {
		return first
	}
	return first + string(os.PathListSeparator) + current
}

func upsertEnv(env []string, key, value string) []string {
	prefix := key + "="
	for i, entry := range env {
		if strings.HasPrefix(entry, prefix) {
			env[i] = prefix + value
			return env
		}
	}
	return append(env, prefix+value)
}

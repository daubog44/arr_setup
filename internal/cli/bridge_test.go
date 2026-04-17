package cli

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func TestTaskBinaryPrefersRepoLocalToolchain(t *testing.T) {
	t.Parallel()

	repoRoot := t.TempDir()
	localTask := filepath.Join(repoRoot, ".tools", runtime.GOOS+"-"+runtime.GOARCH, "bin", taskBinaryName())
	if err := os.MkdirAll(filepath.Dir(localTask), 0o755); err != nil {
		t.Fatalf("mkdir local task dir: %v", err)
	}
	if err := os.WriteFile(localTask, []byte("stub"), 0o755); err != nil {
		t.Fatalf("write local task: %v", err)
	}

	pathTaskDir := t.TempDir()
	pathTask := filepath.Join(pathTaskDir, taskBinaryName())
	if err := os.WriteFile(pathTask, []byte("stub"), 0o755); err != nil {
		t.Fatalf("write PATH task: %v", err)
	}

	originalPath := os.Getenv("PATH")
	if err := os.Setenv("PATH", pathTaskDir+string(os.PathListSeparator)+originalPath); err != nil {
		t.Fatalf("set PATH: %v", err)
	}
	t.Cleanup(func() {
		_ = os.Setenv("PATH", originalPath)
	})

	b := &bridge{repoRoot: repoRoot}
	got, err := b.taskBinary()
	if err != nil {
		t.Fatalf("taskBinary returned error: %v", err)
	}
	if got != localTask {
		t.Fatalf("taskBinary returned %q, want repo-local %q", got, localTask)
	}
}

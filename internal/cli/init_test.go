package cli

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestSeedEnvFileCopiesExampleWhenEnvMissing(t *testing.T) {
	t.Parallel()

	workspaceRoot := t.TempDir()
	examplePath := filepath.Join(workspaceRoot, ".env.example")
	if err := os.WriteFile(examplePath, []byte("DOMAIN_NAME=example.com\n"), 0o644); err != nil {
		t.Fatalf("write .env.example: %v", err)
	}

	created, err := seedEnvFile(workspaceRoot)
	if err != nil {
		t.Fatalf("seedEnvFile returned error: %v", err)
	}
	if !created {
		t.Fatal("seedEnvFile did not report that .env was created")
	}
	data, err := os.ReadFile(filepath.Join(workspaceRoot, ".env"))
	if err != nil {
		t.Fatalf("read .env: %v", err)
	}
	if string(data) != "DOMAIN_NAME=example.com\n" {
		t.Fatalf("unexpected .env contents: %q", string(data))
	}
}

func TestSeedEnvFileDoesNotOverwriteExistingEnv(t *testing.T) {
	t.Parallel()

	workspaceRoot := t.TempDir()
	if err := os.WriteFile(filepath.Join(workspaceRoot, ".env.example"), []byte("DOMAIN_NAME=example.com\n"), 0o644); err != nil {
		t.Fatalf("write .env.example: %v", err)
	}
	if err := os.WriteFile(filepath.Join(workspaceRoot, ".env"), []byte("DOMAIN_NAME=existing.local\n"), 0o600); err != nil {
		t.Fatalf("write .env: %v", err)
	}

	created, err := seedEnvFile(workspaceRoot)
	if err != nil {
		t.Fatalf("seedEnvFile returned error: %v", err)
	}
	if created {
		t.Fatal("seedEnvFile reported creation even though .env already existed")
	}
	data, err := os.ReadFile(filepath.Join(workspaceRoot, ".env"))
	if err != nil {
		t.Fatalf("read existing .env: %v", err)
	}
	if string(data) != "DOMAIN_NAME=existing.local\n" {
		t.Fatalf("existing .env was overwritten: %q", string(data))
	}
}

func TestRenderVersionIncludesBuildMetadata(t *testing.T) {
	t.Parallel()

	originalVersion, originalCommit, originalDate := version, commit, date
	version = "v1.2.3"
	commit = "abc1234"
	date = "2026-04-23T12:00:00Z"
	t.Cleanup(func() {
		version = originalVersion
		commit = originalCommit
		date = originalDate
	})

	rendered := renderVersion()
	for _, expected := range []string{"version: v1.2.3", "commit: abc1234", "built: 2026-04-23T12:00:00Z"} {
		if !containsLine(rendered, expected) {
			t.Fatalf("renderVersion() missing %q in %q", expected, rendered)
		}
	}
}

func containsLine(haystack, needle string) bool {
	for _, line := range strings.Split(haystack, "\n") {
		if line == needle {
			return true
		}
	}
	return false
}

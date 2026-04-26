package cli

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestRootCommandExposesExplicitTaskPassthrough(t *testing.T) {
	t.Parallel()

	for _, cmd := range newRootCmd().Commands() {
		if cmd.Name() == "task" {
			return
		}
	}
	t.Fatal("haac should expose the explicit task passthrough command")
}

func TestTaskCommandRejectsInternalTargets(t *testing.T) {
	t.Parallel()

	if !containsInternalTaskTarget([]string{"internal:configure-apps"}) {
		t.Fatal("internal task target should be rejected by haac task")
	}
	if containsInternalTaskTarget([]string{"verify-web"}) {
		t.Fatal("public task target should be allowed by haac task")
	}
}

func TestRootCommandDoesNotExposeLegacySubcommand(t *testing.T) {
	t.Parallel()

	for _, cmd := range newRootCmd().Commands() {
		if cmd.Name() == "legacy" {
			t.Fatal("legacy subcommand should not be exposed once the Cobra surface is the supported entrypoint")
		}
	}
}

func TestRootCommandDoesNotExposePythonDelegateMaintenanceSubcommands(t *testing.T) {
	t.Parallel()

	required := map[string]struct{}{
		"deploy-argocd":                   {},
		"generate-secrets":                {},
		"generate-secrets-local":          {},
		"push-changes":                    {},
		"wait-for-stack":                  {},
		"reconcile-litmus-admin":          {},
		"reconcile-litmus-chaos":          {},
		"cleanup-security-signal-residue": {},
		"sync-cloudflare":                 {},
		"reconcile-media-stack":           {},
		"verify-arr-flow":                 {},
		"deploy-local":                    {},
		"configure-argocd-local-auth":     {},
		"clean-artifacts":                 {},
		"restore-k3s":                     {},
		"monitor":                         {},
	}

	for _, cmd := range newRootCmd().Commands() {
		delete(required, cmd.Name())
	}
	if len(required) != 0 {
		t.Fatalf("Cobra-owned Go maintenance subcommands are missing: %v", required)
	}
}

func TestProductCommandsDoNotDelegateToTaskOrPython(t *testing.T) {
	t.Parallel()

	_, currentFile, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("unable to resolve current test file")
	}
	cliDir := filepath.Dir(currentFile)
	files := []string{
		"operator.go",
		"operator_engine.go",
		"operator_secrets.go",
		"operator_git.go",
		"operator_argocd.go",
		"operator_cloudflare.go",
		"operator_postinstall.go",
		"operator_maintenance.go",
	}
	for _, file := range files {
		data, err := os.ReadFile(filepath.Join(cliDir, file))
		if err != nil {
			t.Fatalf("read %s: %v", file, err)
		}
		source := string(data)
		for _, forbidden := range []string{
			"runTask" + "InternalTarget",
			"scripts/" + "haac.py",
			"haac." + "ps1",
			"haac." + "sh",
		} {
			if strings.Contains(source, forbidden) {
				t.Fatalf("%s must not contain product-path delegate %q", file, forbidden)
			}
		}
	}
}

func TestDownCommandDoesNotDelegateToInternalTask(t *testing.T) {
	t.Parallel()

	_, currentFile, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("unable to resolve current test file")
	}
	operatorPath := filepath.Join(filepath.Dir(currentFile), "operator.go")
	data, err := os.ReadFile(operatorPath)
	if err != nil {
		t.Fatalf("read operator.go: %v", err)
	}
	source := string(data)
	start := strings.Index(source, "func newDownCmd()")
	if start < 0 {
		t.Fatal("newDownCmd not found")
	}
	end := strings.Index(source[start:], "\nfunc ")
	if end < 0 {
		t.Fatal("newDownCmd end not found")
	}
	body := source[start : start+end]
	if strings.Contains(body, "runTask"+"InternalTarget") || strings.Contains(body, "runTask"+"WithExtraEnv") {
		t.Fatalf("newDownCmd must not delegate to internal Task targets:\n%s", body)
	}
}

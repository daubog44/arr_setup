package cli

import "testing"

func TestWantsTaskPassthrough(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name string
		args []string
		want bool
	}{
		{name: "empty args show cobra help", args: nil, want: false},
		{name: "help subcommand stays local", args: []string{"help"}, want: false},
		{name: "help flag stays local", args: []string{"--help"}, want: false},
		{name: "init stays local", args: []string{"init"}, want: false},
		{name: "install-tools stays local", args: []string{"install-tools"}, want: false},
		{name: "update-tools stays local", args: []string{"update-tools"}, want: false},
		{name: "version subcommand stays local", args: []string{"version"}, want: false},
		{name: "up stays local", args: []string{"up"}, want: false},
		{name: "down stays local", args: []string{"down"}, want: false},
		{name: "preflight stays local", args: []string{"preflight"}, want: false},
		{name: "deploy-argocd passes through to task", args: []string{"deploy-argocd"}, want: true},
		{name: "verify-web passes through to task", args: []string{"verify-web"}, want: true},
		{name: "pre-commit-hook passes through to task", args: []string{"pre-commit-hook"}, want: true},
		{name: "task passthrough keeps global flag ordering", args: []string{"-n", "up"}, want: true},
		{name: "task passthrough keeps explicit subcommand args", args: []string{"plan", "--summary"}, want: true},
	}

	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			if got := wantsTaskPassthrough(tc.args); got != tc.want {
				t.Fatalf("wantsTaskPassthrough(%v) = %v, want %v", tc.args, got, tc.want)
			}
		})
	}
}

func TestContainsInternalTaskTarget(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name string
		args []string
		want bool
	}{
		{name: "public target allowed", args: []string{"up"}, want: false},
		{name: "public namespaced task allowed", args: []string{"reconcile:gitops"}, want: false},
		{name: "internal target blocked", args: []string{"internal:deploy-argocd"}, want: true},
		{name: "internal target blocked behind flag", args: []string{"-n", "internal:deploy-argocd"}, want: true},
	}

	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			if got := containsInternalTaskTarget(tc.args); got != tc.want {
				t.Fatalf("containsInternalTaskTarget(%v) = %v, want %v", tc.args, got, tc.want)
			}
		})
	}
}

func TestEnsurePublicTaskArgs(t *testing.T) {
	t.Parallel()

	if err := ensurePublicTaskArgs([]string{"up"}); err != nil {
		t.Fatalf("ensurePublicTaskArgs rejected a public task: %v", err)
	}
	if err := ensurePublicTaskArgs([]string{"task", "internal:deploy-argocd"}); err == nil {
		t.Fatal("ensurePublicTaskArgs did not reject an internal task")
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

	blocked := map[string]struct{}{
		"clean-artifacts":                 {},
		"deploy-argocd":                   {},
		"deploy-local":                    {},
		"generate-secrets":                {},
		"generate-secrets-local":          {},
		"push-changes":                    {},
		"wait-for-stack":                  {},
		"verify-cluster":                  {},
		"reconcile-litmus-admin":          {},
		"reconcile-litmus-chaos":          {},
		"cleanup-security-signal-residue": {},
		"clear-crowdsec-operator-ban":     {},
		"verify-web":                      {},
		"sync-cloudflare":                 {},
		"configure-apps":                  {},
		"reconcile-media-stack":           {},
		"verify-arr-flow":                 {},
		"configure-argocd-local-auth":     {},
		"restore-k3s":                     {},
		"monitor":                         {},
	}

	for _, cmd := range newRootCmd().Commands() {
		if _, found := blocked[cmd.Name()]; found {
			t.Fatalf("%s should route through public Task targets instead of being exposed as a Cobra-owned maintenance subcommand", cmd.Name())
		}
	}
}

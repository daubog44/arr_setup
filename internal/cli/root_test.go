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
		{name: "install-tools stays local", args: []string{"install-tools"}, want: false},
		{name: "version subcommand stays local", args: []string{"version"}, want: false},
		{name: "task passthrough handles target", args: []string{"up"}, want: true},
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

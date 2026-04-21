package cli

import (
	"fmt"
	"os"
	"strings"

	"github.com/spf13/cobra"
)

var version = "dev"

func Execute() int {
	args := os.Args[1:]
	if wantsTaskPassthrough(args) {
		if err := ensurePublicTaskArgs(args); err != nil {
			fmt.Fprintln(os.Stderr, err)
			return 1
		}
		bridge, err := newBridge()
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			return 1
		}
		if err := bridge.runTask(args); err != nil {
			fmt.Fprintln(os.Stderr, err)
			return 1
		}
		return 0
	}
	if err := newRootCmd().Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 1
	}
	return 0
}

func newRootCmd() *cobra.Command {
	root := &cobra.Command{
		Use:           "haac",
		Short:         "HaaC operator CLI",
		Long:          "HaaC exposes a Cobra-owned operator surface and passes supported task targets through to the repo-local Task binary without a Python fallback.",
		SilenceUsage:  true,
		SilenceErrors: true,
	}

	root.AddCommand(newEnvValueCmd())
	root.AddCommand(newToolPathCmd())
	root.AddCommand(newKubeconfigPathCmd())
	root.AddCommand(newMasterIPCmd())
	root.AddCommand(newProxmoxAccessHostCmd())
	root.AddCommand(newDefaultGatewayCmd())
	root.AddCommand(newInstallToolsCmd())
	root.AddCommand(newInstallWindowsToolsCmd())
	root.AddCommand(newPythonDelegateCmd("check-env", "Validate the required .env inputs and access path", "check-env"))
	root.AddCommand(newPythonDelegateCmd("doctor", "Verify the local workstation toolchain", "doctor"))
	root.AddCommand(newPythonDelegateCmd("install-wsl-tools", "Install required control-node packages inside WSL", "install-wsl-tools"))
	root.AddCommand(newPythonDelegateCmd("clean-artifacts", "Remove local investigation artifacts outside .tmp", "clean-artifacts"))
	root.AddCommand(newPythonDelegateCmd("sync-repo", "Checkpoint and align the GitOps repository state", "sync-repo"))
	root.AddCommand(newPythonDelegateCmd("setup-hooks", "Install the repo pre-commit hook", "setup-hooks"))
	root.AddCommand(newPythonDelegateCmd("run-ansible", "Run the supported Ansible playbook path", "run-ansible"))
	root.AddCommand(newPythonDelegateCmd("run-tofu", "Run OpenTofu with the repo-managed env mapping", "run-tofu"))
	root.AddCommand(newPythonDelegateCmd("deploy-argocd", "Bootstrap or reconcile ArgoCD from the repo-managed overlay", "deploy-argocd"))
	root.AddCommand(newPythonDelegateCmd("deploy-local", "Deploy the local chart when ArgoCD is not already managing it", "deploy-local"))
	root.AddCommand(newPythonDelegateCmd("generate-secrets", "Regenerate repo-managed Sealed Secrets", "generate-secrets"))
	root.AddCommand(newPythonDelegateCmd("generate-secrets-local", "Regenerate repo-managed Sealed Secrets against an existing kubeconfig", "generate-secrets-local"))
	root.AddCommand(newPythonDelegateCmd("push-changes", "Publish generated GitOps artifacts", "push-changes"))
	root.AddCommand(newPythonDelegateCmd("wait-for-stack", "Wait through staged GitOps readiness gates", "wait-for-stack"))
	root.AddCommand(newPythonDelegateCmd("verify-cluster", "Run cluster-level verification checks", "verify-cluster"))
	root.AddCommand(newPythonDelegateCmd("reconcile-litmus-admin", "Repair Litmus admin drift", "reconcile-litmus-admin"))
	root.AddCommand(newPythonDelegateCmd("reconcile-litmus-chaos", "Repair Litmus chaos environment drift", "reconcile-litmus-chaos"))
	root.AddCommand(newPythonDelegateCmd("cleanup-security-signal-residue", "Prune stale security report residue", "cleanup-security-signal-residue"))
	root.AddCommand(newPythonDelegateCmd("clear-crowdsec-operator-ban", "Remove the current operator from CrowdSec temporary bans", "clear-crowdsec-operator-ban"))
	root.AddCommand(newPythonDelegateCmd("verify-web", "Verify the published HTTP endpoints", "verify-web"))
	root.AddCommand(newPythonDelegateCmd("sync-cloudflare", "Reconcile Cloudflare tunnel and DNS state", "sync-cloudflare"))
	root.AddCommand(newPythonDelegateCmd("configure-apps", "Run the supported app bootstrap repair flow", "configure-apps"))
	root.AddCommand(newPythonDelegateCmd("reconcile-media-stack", "Reconcile the repo-managed media stack", "reconcile-media-stack"))
	root.AddCommand(newPythonDelegateCmd("verify-arr-flow", "Run the ARR end-to-end verification path", "verify-arr-flow"))
	root.AddCommand(newPythonDelegateCmd("configure-argocd-local-auth", "Configure the optional local ArgoCD auth fallback", "configure-argocd-local-auth"))
	root.AddCommand(newPythonDelegateCmd("restore-k3s", "Restore K3s from a backup file", "restore-k3s"))
	root.AddCommand(newPythonDelegateCmd("shutdown-cluster", "Gracefully stop the cluster LXC containers", "shutdown-cluster"))
	root.AddCommand(newPythonDelegateCmd("remove-file", "Remove a file path", "remove-file"))
	root.AddCommand(newPythonDelegateCmd("monitor", "Open an interactive cluster monitor session", "monitor"))
	root.AddCommand(newTaskCmd())
	root.AddCommand(newVersionCmd())
	return root
}

func newTaskCmd() *cobra.Command {
	return &cobra.Command{
		Use:                "task [task args...]",
		Short:              "Run a Task target through the repo-local Task binary",
		DisableFlagParsing: true,
		RunE: func(cmd *cobra.Command, args []string) error {
			if err := ensurePublicTaskArgs(args); err != nil {
				return err
			}
			bridge, err := newBridge()
			if err != nil {
				return err
			}
			return bridge.runTask(args)
		},
	}
}

func newVersionCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "version",
		Short: "Print the HaaC CLI version",
		Run: func(cmd *cobra.Command, args []string) {
			fmt.Println(version)
		},
	}
}

func wantsTaskPassthrough(args []string) bool {
	if len(args) == 0 {
		return false
	}
	first := strings.TrimSpace(args[0])
	if first == "" {
		return false
	}
	switch first {
	case "help",
		"env-value",
		"tool-path",
		"kubeconfig-path",
		"master-ip",
		"proxmox-access-host",
		"default-gateway",
		"install-tools",
		"install-windows-tools",
		"install-wsl-tools",
		"check-env",
		"doctor",
		"clean-artifacts",
		"sync-repo",
		"setup-hooks",
		"run-ansible",
		"run-tofu",
		"deploy-argocd",
		"deploy-local",
		"generate-secrets",
		"generate-secrets-local",
		"push-changes",
		"wait-for-stack",
		"verify-cluster",
		"reconcile-litmus-admin",
		"reconcile-litmus-chaos",
		"cleanup-security-signal-residue",
		"clear-crowdsec-operator-ban",
		"verify-web",
		"sync-cloudflare",
		"configure-apps",
		"reconcile-media-stack",
		"verify-arr-flow",
		"configure-argocd-local-auth",
		"restore-k3s",
		"shutdown-cluster",
		"remove-file",
		"monitor",
		"task",
		"version":
		return false
	case "-h", "--help":
		return false
	}
	return true
}

func containsInternalTaskTarget(args []string) bool {
	for _, arg := range args {
		if strings.HasPrefix(strings.TrimSpace(arg), "internal:") {
			return true
		}
	}
	return false
}

func ensurePublicTaskArgs(args []string) error {
	if containsInternalTaskTarget(args) {
		return fmt.Errorf("internal:* Task targets are not part of the supported haac operator surface; use a public task instead")
	}
	return nil
}

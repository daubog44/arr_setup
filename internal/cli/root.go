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
	root.AddCommand(newPreflightCmd())
	root.AddCommand(newCheckEnvCmd())
	root.AddCommand(newDoctorCmd())
	root.AddCommand(newInstallToolsCmd())
	root.AddCommand(newInstallWindowsToolsCmd())
	root.AddCommand(newInstallWSLToolsCmd())
	root.AddCommand(newUpCmd())
	root.AddCommand(newDownCmd())
	root.AddCommand(newSyncRepoCmd())
	root.AddCommand(newSetupHooksCmd())
	root.AddCommand(newRunAnsibleCmd())
	root.AddCommand(newRunTofuCmd())
	root.AddCommand(newShutdownClusterCmd())
	root.AddCommand(newRemoveFileCmd())
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
		"preflight",
		"install-tools",
		"install-windows-tools",
		"install-wsl-tools",
		"check-env",
		"doctor",
		"up",
		"down",
		"sync-repo",
		"setup-hooks",
		"run-ansible",
		"run-tofu",
		"shutdown-cluster",
		"remove-file",
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

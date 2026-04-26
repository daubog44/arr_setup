package cli

import (
	"fmt"
	"os"
	"strings"

	"github.com/spf13/cobra"
)

func Execute() int {
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
		Long:          "HaaC exposes a Cobra-owned operator surface, can initialize a workspace from Git, and runs the supported homelab bootstrap without Python or Task backend delegation. The explicit `haac task` command remains as a public Task passthrough for compatibility aliases.",
		SilenceUsage:  true,
		SilenceErrors: true,
	}

	root.AddCommand(newInitCmd())
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
	root.AddCommand(newUpdateToolsCmd())
	root.AddCommand(newInstallWindowsToolsCmd())
	root.AddCommand(newInstallWSLToolsCmd())
	root.AddCommand(newUpCmd())
	root.AddCommand(newDownCmd())
	root.AddCommand(newGenerateSecretsCmd(true))
	root.AddCommand(newGenerateSecretsCmd(false))
	root.AddCommand(newPushChangesCmd())
	root.AddCommand(newDeployArgoCDCmd())
	root.AddCommand(newWaitForStackCmd())
	root.AddCommand(newSyncCloudflareCmd())
	root.AddCommand(newReconcileLitmusAdminCmd())
	root.AddCommand(newReconcileLitmusChaosCmd())
	root.AddCommand(newReconcileMediaStackCmd())
	root.AddCommand(newVerifyARRFlowCmd())
	root.AddCommand(newCleanupSecuritySignalResidueCmd())
	root.AddCommand(newDeployLocalCmd())
	root.AddCommand(newConfigureArgoCDLocalAuthCmd())
	root.AddCommand(newCleanArtifactsCmd())
	root.AddCommand(newRestoreK3sCmd())
	root.AddCommand(newMonitorCmd())
	root.AddCommand(newVerifyWebCmd())
	root.AddCommand(newDiagnoseEdgeCmd())
	root.AddCommand(newVerifyClusterCmd())
	root.AddCommand(newKubectlCmd())
	root.AddCommand(newVerifyBrowserAuthCmd())
	root.AddCommand(newClearCrowdSecOperatorBanCmd())
	root.AddCommand(newTaskCmd())
	root.AddCommand(newSyncRepoCmd())
	root.AddCommand(newSetupHooksCmd())
	root.AddCommand(newPreCommitHookCmd())
	root.AddCommand(newRunAnsibleCmd())
	root.AddCommand(newRunTofuCmd())
	root.AddCommand(newShutdownClusterCmd())
	root.AddCommand(newRemoveFileCmd())
	root.AddCommand(newVersionCmd())
	return root
}

func newTaskCmd() *cobra.Command {
	return &cobra.Command{
		Use:                "task [task args...]",
		Short:              "Run a Task target through the repo-local Task binary",
		DisableFlagParsing: true,
		RunE: func(cmd *cobra.Command, args []string) error {
			if containsInternalTaskTarget(args) {
				return fmt.Errorf("internal:* Task targets are not part of the supported haac operator surface; use a public task instead")
			}
			b, err := newBridge()
			if err != nil {
				return err
			}
			return b.runTask(args)
		},
	}
}

func containsInternalTaskTarget(args []string) bool {
	for _, arg := range args {
		if strings.HasPrefix(strings.TrimSpace(arg), "internal:") {
			return true
		}
	}
	return false
}

func newVersionCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "version",
		Short: "Print the HaaC CLI version",
		Run: func(cmd *cobra.Command, args []string) {
			fmt.Println(renderVersion())
		},
	}
}

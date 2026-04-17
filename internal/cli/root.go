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
		Short:         "Staged HaaC operator CLI",
		Long:          "HaaC keeps Task as the product surface. Known maintenance commands live here, and any other arguments pass through to Task unchanged.",
		SilenceUsage:  true,
		SilenceErrors: true,
	}

	root.AddCommand(newTaskCmd())
	root.AddCommand(newLegacyCmd())
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

func newLegacyCmd() *cobra.Command {
	return &cobra.Command{
		Use:                "legacy [haac.py args...]",
		Short:              "Run the legacy Python CLI directly",
		Hidden:             true,
		DisableFlagParsing: true,
		RunE: func(cmd *cobra.Command, args []string) error {
			bridge, err := newBridge()
			if err != nil {
				return err
			}
			return bridge.runLegacy(args)
		},
	}
}

func newVersionCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "version",
		Short: "Print the staged Cobra foundation version",
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
	case "help", "legacy", "task", "version":
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

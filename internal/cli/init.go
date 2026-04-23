package cli

import (
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/spf13/cobra"
)

const defaultInitRepoURL = "https://github.com/daubog44/arr_setup.git"

func newInitCmd() *cobra.Command {
	var repoURL string
	var revision string
	var installToolsAfterInit bool
	var toolScope string

	cmd := &cobra.Command{
		Use:   "init [directory]",
		Short: "Clone a HaaC workspace from Git and seed the local .env scaffold",
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) > 1 {
				return fmt.Errorf("init accepts at most one target directory")
			}
			target := "."
			if len(args) == 1 {
				target = args[0]
			}
			workspaceRoot, err := initWorkspace(target, repoURL, revision)
			if err != nil {
				return err
			}
			if installToolsAfterInit {
				return installTools(toolInstallOptions{
					workspaceRoot:   workspaceRoot,
					scope:           strings.TrimSpace(toolScope),
					upgrade:         false,
					withControlNode: true,
				})
			}
			return nil
		},
	}
	cmd.Flags().StringVar(&repoURL, "repo", defaultInitRepoURL, "Git repository URL to clone")
	cmd.Flags().StringVar(&revision, "revision", "", "Git branch or revision to clone")
	cmd.Flags().BoolVar(&installToolsAfterInit, "install-tools", false, "Install the managed toolchain after cloning")
	cmd.Flags().StringVar(&toolScope, "tool-scope", string(toolInstallScopeLocal), "Tool install scope to use when --install-tools is set (local or global)")
	return cmd
}

func initWorkspace(targetDir, repoURL, revision string) (string, error) {
	gitBinary, err := exec.LookPath("git")
	if err != nil {
		return "", fmt.Errorf("git is required for `haac init`")
	}
	workspaceRoot, err := resolveTargetPath(targetDir)
	if err != nil {
		return "", err
	}
	if info, err := os.Stat(workspaceRoot); err == nil {
		if !info.IsDir() {
			return "", fmt.Errorf("%s already exists and is not a directory", workspaceRoot)
		}
		empty, err := directoryEmpty(workspaceRoot)
		if err != nil {
			return "", err
		}
		if !empty {
			return "", fmt.Errorf("%s already exists and is not empty", workspaceRoot)
		}
	} else if !os.IsNotExist(err) {
		return "", err
	}

	args := []string{"clone"}
	if strings.TrimSpace(revision) != "" {
		args = append(args, "--branch", strings.TrimSpace(revision), "--single-branch")
	}
	args = append(args, strings.TrimSpace(repoURL), workspaceRoot)
	cmd := exec.Command(gitBinary, args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin
	if err := cmd.Run(); err != nil {
		return "", err
	}

	createdEnv, err := seedEnvFile(workspaceRoot)
	if err != nil {
		return "", err
	}
	fmt.Printf("Initialized HaaC workspace at %s\n", workspaceRoot)
	if createdEnv {
		fmt.Printf("Seeded %s from .env.example\n", filepath.Join(workspaceRoot, ".env"))
	}
	fmt.Println("Next required step: fill the local .env file, then run `haac install-tools` and `haac up` inside that workspace.")
	return workspaceRoot, nil
}

func seedEnvFile(workspaceRoot string) (bool, error) {
	envPath := filepath.Join(workspaceRoot, ".env")
	if fileExists(envPath) {
		return false, nil
	}
	envExamplePath := filepath.Join(workspaceRoot, ".env.example")
	if !fileExists(envExamplePath) {
		return false, nil
	}
	source, err := os.Open(envExamplePath)
	if err != nil {
		return false, err
	}
	defer source.Close()

	destination, err := os.OpenFile(envPath, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0o600)
	if err != nil {
		return false, err
	}
	defer destination.Close()

	if _, err := io.Copy(destination, source); err != nil {
		return false, err
	}
	return true, nil
}

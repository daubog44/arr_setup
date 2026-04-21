package cli

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/spf13/cobra"
)

func pythonBinary() (string, error) {
	if requested := strings.TrimSpace(os.Getenv("PYTHON_CMD")); requested != "" {
		if binary, err := exec.LookPath(requested); err == nil {
			return binary, nil
		}
	}
	candidates := []string{"python3", "python"}
	if runtime.GOOS == "windows" {
		candidates = []string{"python", "python3"}
	}
	for _, candidate := range candidates {
		if binary, err := exec.LookPath(candidate); err == nil {
			return binary, nil
		}
	}
	return "", fmt.Errorf("python interpreter not found")
}

func runPythonDelegate(repoRoot string, args []string) error {
	python, err := pythonBinary()
	if err != nil {
		return err
	}
	commandArgs := append([]string{filepath.Join(repoRoot, "scripts", "haac.py")}, args...)
	cmd := exec.Command(python, commandArgs...)
	cmd.Dir = repoRoot
	cmd.Env = os.Environ()
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin
	if err := cmd.Run(); err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			return fmt.Errorf("command failed with exit code %d", exitErr.ExitCode())
		}
		return err
	}
	return nil
}

func newPythonDelegateCmd(use, short, pythonCommand string) *cobra.Command {
	return &cobra.Command{
		Use:                use,
		Short:              short,
		DisableFlagParsing: true,
		RunE: func(cmd *cobra.Command, args []string) error {
			b, err := newBridge()
			if err != nil {
				return err
			}
			delegateArgs := append([]string{pythonCommand}, args...)
			return runPythonDelegate(b.repoRoot, delegateArgs)
		},
	}
}

package cli

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/spf13/cobra"
)

func newEnvValueCmd() *cobra.Command {
	var defaultValue string
	cmd := &cobra.Command{
		Use:   "env-value --name <NAME>",
		Short: "Resolve an environment value from .env plus process env",
		RunE: func(cmd *cobra.Command, args []string) error {
			name, _ := cmd.Flags().GetString("name")
			if strings.TrimSpace(name) == "" {
				return fmt.Errorf("--name is required")
			}
			repoRoot, err := repoRoot()
			if err != nil {
				return err
			}
			env, err := mergedEnvFromRepo(repoRoot)
			if err != nil {
				return err
			}
			value := env[name]
			if value == "" {
				value = defaultValue
			}
			fmt.Println(value)
			return nil
		},
	}
	cmd.Flags().String("name", "", "Environment variable name")
	cmd.Flags().StringVar(&defaultValue, "default", "", "Fallback value")
	return cmd
}

func newKubeconfigPathCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "kubeconfig-path",
		Short: "Print the repo-local kubeconfig path",
		RunE: func(cmd *cobra.Command, args []string) error {
			fmt.Println(localKubeconfigPathGo())
			return nil
		},
	}
}

func newProxmoxAccessHostCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "proxmox-access-host",
		Short: "Print the effective workstation-reachable Proxmox host",
		RunE: func(cmd *cobra.Command, args []string) error {
			repoRoot, err := repoRoot()
			if err != nil {
				return err
			}
			env, err := mergedEnvFromRepo(repoRoot)
			if err != nil {
				return err
			}
			fmt.Println(proxmoxAccessHostGo(env))
			return nil
		},
	}
}

func newMasterIPCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "master-ip",
		Short: "Print the effective K3s master IP",
		RunE: func(cmd *cobra.Command, args []string) error {
			repoRoot, err := repoRoot()
			if err != nil {
				return err
			}
			env, err := mergedEnvFromRepo(repoRoot)
			if err != nil {
				return err
			}
			fmt.Println(resolvedMasterIPValueGo(repoRoot, env))
			return nil
		},
	}
}

func newToolPathCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "tool-path --name <tool>",
		Short: "Resolve the effective tool path for the supported operator toolchain",
		RunE: func(cmd *cobra.Command, args []string) error {
			name, _ := cmd.Flags().GetString("name")
			if strings.TrimSpace(name) == "" {
				return fmt.Errorf("--name is required")
			}
			repoRoot, err := repoRoot()
			if err != nil {
				return err
			}
			env, err := mergedEnvFromRepo(repoRoot)
			if err != nil {
				return err
			}
			if isBootstrappableTool(name) {
				path, err := ensureLocalCLITool(repoRoot, name, runtime.GOOS, runtime.GOARCH, env)
				if err != nil {
					return err
				}
				fmt.Println(path)
				return nil
			}
			location, err := exec.LookPath(name)
			if err != nil {
				return err
			}
			fmt.Println(location)
			return nil
		},
	}
	cmd.Flags().String("name", "", "Tool name")
	return cmd
}

func newInstallWindowsToolsCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "install-windows-tools",
		Short: "Compatibility alias for install-tools",
		RunE: func(cmd *cobra.Command, args []string) error {
			b, err := newBridge()
			if err != nil {
				return err
			}
			return installTools(b.repoRoot)
		},
	}
}

func localKubeconfigPathGo() string {
	if override := strings.TrimSpace(os.Getenv("HAAC_KUBECONFIG_PATH")); override != "" {
		return override
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return filepath.Join(".kube", "haac-k3s.yaml")
	}
	return filepath.Join(home, ".kube", "haac-k3s.yaml")
}

func proxmoxAccessHostGo(env map[string]string) string {
	if value := strings.TrimSpace(env["PROXMOX_ACCESS_HOST"]); value != "" {
		return value
	}
	if value := strings.TrimSpace(env["MASTER_TARGET_NODE"]); value != "" {
		return value
	}
	return "pve"
}

func stripIPCIDRGo(value string) string {
	return strings.TrimSpace(strings.Split(strings.TrimSpace(value), "/")[0])
}

func resolvedMasterIPValueGo(repoRoot string, env map[string]string) string {
	if declared := stripIPCIDRGo(env["K3S_MASTER_IP"]); declared != "" {
		return declared
	}
	if value := strings.TrimSpace(tofuOutputValueGo(filepath.Join(repoRoot, "tofu"), "master_ip")); value != "" {
		return stripIPCIDRGo(value)
	}
	return "127.0.0.1"
}

func tofuOutputValueGo(tofuDir, name string) string {
	tofuPath := toolLocationGo(filepath.Dir(tofuDir), "tofu")
	if tofuPath == "" {
		return ""
	}
	cmd := exec.Command(tofuPath, "-chdir="+tofuDir, "output", "-json", "-no-color")
	cmd.Stdout = nil
	output, err := cmd.Output()
	if err != nil || len(output) == 0 || output[0] != '{' {
		return ""
	}
	var payload map[string]struct {
		Value any `json:"value"`
	}
	if err := json.Unmarshal(output, &payload); err != nil {
		return ""
	}
	item, ok := payload[name]
	if !ok || item.Value == nil {
		return ""
	}
	switch value := item.Value.(type) {
	case string:
		return strings.TrimSpace(value)
	case float64:
		return strings.TrimRight(strings.TrimRight(fmt.Sprintf("%f", value), "0"), ".")
	case bool:
		if value {
			return "true"
		}
		return "false"
	default:
		rendered, err := json.Marshal(value)
		if err != nil {
			return ""
		}
		return string(rendered)
	}
}

func toolLocationGo(repoRoot, name string) string {
	local := repoLocalBinaryPath(repoRoot, name, runtime.GOOS, runtime.GOARCH)
	if fileExists(local) {
		return local
	}
	if found, err := exec.LookPath(name); err == nil {
		return found
	}
	return ""
}

func isBootstrappableTool(name string) bool {
	switch name {
	case "tofu", "helm", "kubectl", "kubeseal", "task":
		return true
	default:
		return false
	}
}

package cli

import (
	"errors"
	"fmt"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"runtime"
	"strings"
	"time"

	"github.com/spf13/cobra"
)

var (
	ipV4Pattern = regexp.MustCompile(`\b(?:\d{1,3}\.){3}\d{1,3}\b`)
)

func newPreflightCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "preflight",
		Short: "Run the supported ordered bootstrap preflight",
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) != 0 {
				return fmt.Errorf("preflight does not accept extra arguments")
			}
			if err := runCheckEnv(); err != nil {
				return err
			}
			return runDoctor()
		},
	}
}

func newCheckEnvCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "check-env",
		Short: "Validate the required .env inputs and access path",
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) != 0 {
				return fmt.Errorf("check-env does not accept extra arguments")
			}
			return runCheckEnv()
		},
	}
}

func newDoctorCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "doctor",
		Short: "Verify the local workstation toolchain",
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) != 0 {
				return fmt.Errorf("doctor does not accept extra arguments")
			}
			return runDoctor()
		},
	}
}

func newInstallWSLToolsCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "install-wsl-tools",
		Short: "Install required control-node packages inside WSL",
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) != 0 {
				return fmt.Errorf("install-wsl-tools does not accept extra arguments")
			}
			if runtime.GOOS != "windows" {
				return fmt.Errorf("install-wsl-tools is supported only on Windows")
			}
			b, err := newBridge()
			if err != nil {
				return err
			}
			env, err := mergedEnvFromRepo(b.repoRoot)
			if err != nil {
				return err
			}
			return installWSLTools(env)
		},
	}
}

func newDefaultGatewayCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "default-gateway",
		Short: "Resolve the effective default gateway for OpenTofu TF vars",
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) != 0 {
				return fmt.Errorf("default-gateway does not accept extra arguments")
			}
			b, err := newBridge()
			if err != nil {
				return err
			}
			env, err := mergedEnvFromRepo(b.repoRoot)
			if err != nil {
				return err
			}
			fmt.Println(resolveDefaultGatewayGo(env))
			return nil
		},
	}
}

func newRunTofuCmd() *cobra.Command {
	var dir string
	cmd := &cobra.Command{
		Use:   "run-tofu [tofu args...]",
		Short: "Run OpenTofu with the repo-managed env mapping",
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 {
				return fmt.Errorf("run-tofu requires the OpenTofu arguments after --, for example: run-tofu --dir tofu apply -auto-approve")
			}
			b, err := newBridge()
			if err != nil {
				return err
			}
			return runTofuCommandGo(b.repoRoot, dir, args)
		},
	}
	cmd.Flags().StringVar(&dir, "dir", "tofu", "OpenTofu working directory")
	return cmd
}

func newRunAnsibleCmd() *cobra.Command {
	var inventory string
	var playbook string
	var extraArgs string
	cmd := &cobra.Command{
		Use:   "run-ansible",
		Short: "Run the supported Ansible playbook path",
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) != 0 {
				return fmt.Errorf("run-ansible accepts flags only")
			}
			b, err := newBridge()
			if err != nil {
				return err
			}
			return runAnsibleCommandGo(b.repoRoot, inventory, playbook, extraArgs)
		},
	}
	cmd.Flags().StringVar(&inventory, "inventory", "ansible/inventory.yml", "Inventory file path")
	cmd.Flags().StringVar(&playbook, "playbook", "ansible/playbook.yml", "Playbook file path")
	cmd.Flags().StringVar(&extraArgs, "extra-args", "", "Additional ansible-playbook arguments")
	return cmd
}

func newSetupHooksCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "setup-hooks",
		Short: "Install the repo pre-commit hook",
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) != 0 {
				return fmt.Errorf("setup-hooks does not accept extra arguments")
			}
			b, err := newBridge()
			if err != nil {
				return err
			}
			return installHooksGo(b.repoRoot)
		},
	}
}

func newSyncRepoCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "sync-repo",
		Short: "Checkpoint and align the GitOps repository state",
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) != 0 {
				return fmt.Errorf("sync-repo does not accept extra arguments")
			}
			b, err := newBridge()
			if err != nil {
				return err
			}
			return syncRepoGo(b.repoRoot)
		},
	}
}

func newUpCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "up",
		Short: "Run the full supported bootstrap path",
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) != 0 {
				return fmt.Errorf("up does not accept extra arguments")
			}
			b, err := newBridge()
			if err != nil {
				return err
			}
			return runOperatorUpGo(b.repoRoot)
		},
	}
}

func newDownCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "down",
		Short: "Gracefully stop the cluster and destroy the infrastructure",
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) != 0 {
				return fmt.Errorf("down does not accept extra arguments")
			}
			b, err := newBridge()
			if err != nil {
				return err
			}
			return runOperatorDownGo(b.repoRoot)
		},
	}
}

func newShutdownClusterCmd() *cobra.Command {
	var proxmoxHost string
	var tofuDir string
	cmd := &cobra.Command{
		Use:   "shutdown-cluster",
		Short: "Gracefully stop the cluster LXC containers",
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) != 0 {
				return fmt.Errorf("shutdown-cluster accepts flags only")
			}
			b, err := newBridge()
			if err != nil {
				return err
			}
			return shutdownClusterGo(b.repoRoot, proxmoxHost, tofuDir)
		},
	}
	cmd.Flags().StringVar(&proxmoxHost, "proxmox-host", "", "Workstation-reachable Proxmox host override")
	cmd.Flags().StringVar(&tofuDir, "tofu-dir", "tofu", "OpenTofu working directory")
	return cmd
}

func newRemoveFileCmd() *cobra.Command {
	var path string
	cmd := &cobra.Command{
		Use:   "remove-file --path <path>",
		Short: "Remove a file path",
		RunE: func(cmd *cobra.Command, args []string) error {
			if strings.TrimSpace(path) == "" {
				return fmt.Errorf("--path is required")
			}
			b, err := newBridge()
			if err != nil {
				return err
			}
			return removeFileGo(filepath.Join(b.repoRoot, filepath.FromSlash(path)))
		},
	}
	cmd.Flags().StringVar(&path, "path", "", "Relative or absolute file path")
	return cmd
}

func runCheckEnv() error {
	b, err := newBridge()
	if err != nil {
		return err
	}
	env, err := mergedEnvFromRepo(b.repoRoot)
	if err != nil {
		return err
	}
	if !fileExists(filepath.Join(b.repoRoot, ".env")) {
		return fmt.Errorf("please create a .env file based on .env.example")
	}
	if err := applyIdentityDefaultsGo(env); err != nil {
		return err
	}
	if err := requireEnvKeysGo(env, []string{
		"LXC_PASSWORD",
		"LXC_MASTER_HOSTNAME",
		"DOMAIN_NAME",
		"NAS_ADDRESS",
		"HOST_NAS_PATH",
		"NAS_PATH",
		"NAS_SHARE_NAME",
		"SMB_USER",
		"SMB_PASSWORD",
		"STORAGE_UID",
		"STORAGE_GID",
		"GITOPS_REPO_URL",
		"GITOPS_REPO_REVISION",
		"CLOUDFLARE_API_TOKEN",
		"CLOUDFLARE_ACCOUNT_ID",
		"CLOUDFLARE_ZONE_ID",
		"CLOUDFLARE_TUNNEL_TOKEN",
	}); err != nil {
		return err
	}
	if err := requireEnvKeysGo(env, []string{
		"AUTHELIA_ADMIN_PASSWORD",
		"GRAFANA_ADMIN_PASSWORD",
		"LITMUS_ADMIN_PASSWORD",
		"LITMUS_MONGODB_ROOT_PASSWORD",
		"LITMUS_MONGODB_REPLICA_SET_KEY",
		"SEMAPHORE_ADMIN_PASSWORD",
		"QUI_PASSWORD",
	}); err != nil {
		return err
	}
	accessHost := proxmoxAccessHostGo(env)
	hint := "Set PROXMOX_ACCESS_HOST to the workstation-reachable Proxmox IP/FQDN, or ensure MASTER_TARGET_NODE resolves locally before running `haac up`."
	if err := ensureTCPEndpointGo(accessHost, 8006, "Proxmox API", hint); err != nil {
		return err
	}
	if err := ensureTCPEndpointGo(accessHost, 22, "Proxmox SSH", hint); err != nil {
		return err
	}
	warnSharedCredentialScopeGo(env)
	return nil
}

func runDoctor() error {
	b, err := newBridge()
	if err != nil {
		return err
	}
	env, err := mergedEnvFromRepo(b.repoRoot)
	if err != nil {
		return err
	}
	if err := applyIdentityDefaultsGo(env); err != nil {
		return err
	}
	repoKey := filepath.Join(b.repoRoot, ".ssh", "haac_ed25519")
	semaphoreKey := filepath.Join(b.repoRoot, ".ssh", "haac_semaphore_ed25519")
	repoDeployKey := filepath.Join(b.repoRoot, ".ssh", "haac_repo_deploy_ed25519")
	if err := ensureSSHKeypair(repoKey, "haac@local"); err != nil {
		return err
	}
	if err := ensureSSHKeypair(repoDeployKey, "haac-repo-deploy@local"); err != nil {
		return err
	}
	knownHosts := ensureKnownHostsPathGo(b.repoRoot, env)

	failures := make([]string, 0)
	checks := [][2]string{
		{"git", "git"},
		{"ssh", "ssh"},
		{"node", "node"},
		{"kubectl", "kubectl"},
		{"tofu", "tofu"},
		{"helm", "helm"},
		{"kubeseal", "kubeseal"},
	}
	if runtime.GOOS == "windows" {
		checks = append(checks, [2]string{"wsl", "wsl"})
	} else {
		checks = append(checks, [2]string{"ansible-playbook", "ansible-playbook"})
	}
	for _, check := range checks {
		location := ""
		if isBootstrappableTool(check[1]) {
			location = toolLocationGo(b.repoRoot, check[1])
		} else if check[1] == "ansible-playbook" {
			location = findManagedAnsibleBinary(b.repoRoot)
			if location == "" {
				if found, err := exec.LookPath(check[1]); err == nil {
					location = found
				}
			}
		} else if found, err := exec.LookPath(check[1]); err == nil {
			location = found
		}
		if strings.TrimSpace(location) != "" {
			fmt.Printf("[ok] %s: %s\n", check[0], location)
		} else {
			fmt.Printf("[missing] %s\n", check[0])
			failures = append(failures, check[0])
		}
	}

	if fileExists(repoKey) && fileExists(repoKey+".pub") {
		fmt.Printf("[ok] repo ssh keypair: %s\n", repoKey)
	} else {
		fmt.Printf("[missing] repo ssh keypair: %s\n", repoKey)
		failures = append(failures, "repo-ssh-keypair")
	}
	if fileExists(semaphoreKey) && fileExists(semaphoreKey+".pub") {
		fmt.Printf("[ok] semaphore maintenance ssh keypair: %s\n", semaphoreKey)
	} else {
		fmt.Printf("[warn] semaphore maintenance ssh keypair missing: %s (it will be created during `haac up` before cluster publication)\n", semaphoreKey)
	}
	if fileExists(repoDeployKey) && fileExists(repoDeployKey+".pub") {
		fmt.Printf("[ok] repo deploy ssh keypair: %s\n", repoDeployKey)
	} else {
		fmt.Printf("[missing] repo deploy ssh keypair: %s\n", repoDeployKey)
		failures = append(failures, "repo-deploy-ssh-keypair")
	}
	fmt.Printf("[ok] known_hosts path: %s\n", knownHosts)

	if runtime.GOOS == "windows" {
		distro := wslDistro(env)
		if !wslDistroExists(env) {
			fmt.Printf("[missing] wsl distro: %s\n", distro)
			failures = append(failures, "wsl-distro:"+distro)
		} else {
			fmt.Printf("[ok] wsl distro: %s\n", distro)
			linuxArch, err := detectWSLArch(env)
			if err != nil {
				return err
			}
			for _, binary := range []string{"tofu", "helm", "kubectl", "kubeseal"} {
				linuxTool := repoLocalBinaryPath(b.repoRoot, binary, "linux", linuxArch)
				if fileExists(linuxTool) {
					fmt.Printf("[ok] portable linux tool (%s): %s\n", binary, linuxTool)
				} else {
					fmt.Printf("[missing] portable linux tool (%s)\n", binary)
					failures = append(failures, "portable-linux:"+binary)
				}
			}
			for _, check := range [][2]string{
				{"ansible-playbook", "command -v ansible-playbook"},
				{"git", "command -v git"},
				{"python3", "command -v python3"},
				{"ssh", "command -v ssh"},
			} {
				location, err := runWSLOutputWithRetries(env, "bash", "-lc", check[1])
				if err == nil && location != "" {
					fmt.Printf("[ok] %s:%s: %s\n", distro, check[0], location)
				} else {
					fmt.Printf("[missing] %s:%s\n", distro, check[0])
					failures = append(failures, distro+":"+check[0])
				}
			}
		}
	}

	if len(failures) != 0 {
		return fmt.Errorf("missing required tooling: %s", strings.Join(failures, ", "))
	}
	fmt.Println("Doctor checks local tooling only. Run `haac check-env` before `haac up` to verify workstation-to-Proxmox reachability.")
	return nil
}

func resolveDefaultGatewayGo(env map[string]string) string {
	if value := strings.TrimSpace(env["LXC_GATEWAY"]); value != "" {
		return value
	}
	host := proxmoxAccessHostGo(env)
	output, err := runProxmoxSSHStdoutGo(env, host, "ip route | awk '/default/ {print $3; exit}'", 5, false)
	if err != nil {
		return ""
	}
	output = strings.TrimSpace(output)
	if output == "" {
		return ""
	}
	if match := ipV4Pattern.FindString(output); match != "" {
		return match
	}
	return output
}

func runTofuCommandGo(repoRoot, dir string, arguments []string) error {
	env, err := mergedEnvFromRepo(repoRoot)
	if err != nil {
		return err
	}
	if err := applyIdentityDefaultsGo(env); err != nil {
		return err
	}
	tofuBinary, err := ensureLocalCLITool(repoRoot, "tofu", runtime.GOOS, runtime.GOARCH, env)
	if err != nil {
		return err
	}
	tofuDir := filepath.Join(repoRoot, filepath.FromSlash(strings.TrimSpace(dir)))
	if len(arguments) > 0 && (arguments[0] == "plan" || arguments[0] == "apply") {
		if err := migrateLegacyProxmoxDownloadFileStateGo(repoRoot, tofuDir, tofuBinary, env); err != nil {
			return err
		}
	}
	commandArgs := append([]string{"-chdir=" + tofuDir}, arguments...)
	cmd := exec.Command(tofuBinary, commandArgs...)
	cmd.Dir = repoRoot
	cmd.Env = tofuCLIEnvGo(repoRoot, env)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin
	if err := cmd.Run(); err != nil {
		var exitErr *exec.ExitError
		if errors.As(err, &exitErr) {
			return fmt.Errorf("command failed with exit code %d", exitErr.ExitCode())
		}
		return err
	}
	return nil
}

func runAnsibleCommandGo(repoRoot, inventory, playbook, extraArgs string) error {
	env, err := mergedEnvFromRepo(repoRoot)
	if err != nil {
		return err
	}
	if err := applyIdentityDefaultsGo(env); err != nil {
		return err
	}
	repoKey := filepath.Join(repoRoot, ".ssh", "haac_ed25519")
	semaphoreKey := filepath.Join(repoRoot, ".ssh", "haac_semaphore_ed25519")
	if err := ensureSSHKeypair(repoKey, "haac@local"); err != nil {
		return err
	}
	if err := ensureSSHKeypair(semaphoreKey, "haac-semaphore@local"); err != nil {
		return err
	}
	if err := refreshClusterKnownHostsGo(repoRoot, env, 120*time.Second); err != nil {
		return err
	}
	inventoryPath := filepath.Join(repoRoot, filepath.FromSlash(inventory))
	playbookPath := filepath.Join(repoRoot, filepath.FromSlash(playbook))
	args := []string{}
	if strings.TrimSpace(extraArgs) != "" {
		args = append(args, strings.Fields(extraArgs)...)
	}
	if runtime.GOOS == "windows" {
		return runAnsibleWSLGo(repoRoot, inventoryPath, playbookPath, args, env)
	}
	ansibleBinary := findManagedAnsibleBinary(repoRoot)
	if ansibleBinary == "" {
		resolved, err := exec.LookPath("ansible-playbook")
		if err != nil {
			return fmt.Errorf("ansible-playbook not found; run `haac install-tools --scope local --with-control-node` or install it globally")
		}
		ansibleBinary = resolved
	}
	commandArgs := append(args, "-i", inventoryPath, playbookPath)
	cmd := exec.Command(ansibleBinary, commandArgs...)
	cmd.Dir = repoRoot
	cmd.Env = ansibleEnvGo(repoRoot, env, repoKey, ensureKnownHostsPathGo(repoRoot, env))
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin
	if err := cmd.Run(); err != nil {
		var exitErr *exec.ExitError
		if errors.As(err, &exitErr) {
			return fmt.Errorf("command failed with exit code %d", exitErr.ExitCode())
		}
		return err
	}
	return nil
}

func installHooksGo(repoRoot string) error {
	gitHooksDir := filepath.Join(repoRoot, ".git", "hooks")
	if info, err := os.Stat(gitHooksDir); err != nil || !info.IsDir() {
		fmt.Println("Skipping hook installation: .git/hooks not found.")
		return nil
	}

	hookPath := filepath.Join(gitHooksDir, "pre-commit")
	hookContent := "#!/usr/bin/env sh\nset -eu\ncommand -v haac >/dev/null 2>&1 || { echo 'haac CLI not found on PATH; install the Go binary before using this hook.' >&2; exit 1; }\nexec haac pre-commit-hook\n"
	if err := os.WriteFile(hookPath, []byte(hookContent), 0o755); err != nil {
		return err
	}
	hookCmdPath := filepath.Join(gitHooksDir, "pre-commit.cmd")
	hookCmdContent := "@echo off\r\nwhere haac >nul 2>nul\r\nif errorlevel 1 (\r\n  echo haac CLI not found on PATH; install the Go binary before using this hook.\r\n  exit /b 1\r\n)\r\nhaac pre-commit-hook\r\nexit /b %ERRORLEVEL%\r\n"
	return os.WriteFile(hookCmdPath, []byte(hookCmdContent), 0o644)
}

func shutdownClusterGo(repoRoot, proxmoxHost, tofuDir string) error {
	env, err := mergedEnvFromRepo(repoRoot)
	if err != nil {
		return err
	}
	if err := applyIdentityDefaultsGo(env); err != nil {
		return err
	}
	host := strings.TrimSpace(proxmoxHost)
	if host == "" {
		host = proxmoxAccessHostGo(env)
	}
	tofuBinary, err := ensureLocalCLITool(repoRoot, "tofu", runtime.GOOS, runtime.GOARCH, env)
	if err != nil {
		return err
	}
	tofuPath := filepath.Join(repoRoot, filepath.FromSlash(tofuDir))
	masterVMID, err := tofuOutputRawGo(repoRoot, tofuBinary, tofuPath, "master_vmid")
	if err != nil {
		return err
	}
	workerJSON, err := tofuOutputJSONValueGo(repoRoot, tofuBinary, tofuPath, "workers")
	if err != nil {
		return err
	}

	type labeledVMID struct {
		vmid  string
		label string
	}
	targets := make([]labeledVMID, 0)
	if strings.TrimSpace(masterVMID) != "" {
		targets = append(targets, labeledVMID{vmid: strings.TrimSpace(masterVMID), label: "Master"})
	}
	if workerMap, ok := workerJSON.(map[string]any); ok {
		index := 1
		for _, rawWorker := range workerMap {
			worker, ok := rawWorker.(map[string]any)
			if !ok {
				continue
			}
			vmid := strings.TrimSpace(fmt.Sprint(worker["vmid"]))
			if vmid == "" || vmid == "<nil>" {
				continue
			}
			targets = append(targets, labeledVMID{vmid: vmid, label: fmt.Sprintf("Worker %d", index)})
			index++
		}
	}

	for _, target := range targets {
		status, err := runProxmoxSSHStdoutGo(env, host, fmt.Sprintf("pct status %s", shellEscape(target.vmid)), 5, false)
		if err != nil {
			return err
		}
		if !strings.Contains(status, "status: running") {
			continue
		}
		_, _ = runProxmoxSSHStdoutGo(
			env,
			host,
			fmt.Sprintf("pct exec %s -- bash -lc 'systemctl stop k3s 2>/dev/null || true; systemctl stop k3s-agent 2>/dev/null || true'", shellEscape(target.vmid)),
			5,
			false,
		)
		if _, err := runProxmoxSSHStdoutGo(env, host, fmt.Sprintf("pct shutdown %s --timeout 180", shellEscape(target.vmid)), 5, false); err != nil {
			_, _ = runProxmoxSSHStdoutGo(env, host, fmt.Sprintf("pct stop %s", shellEscape(target.vmid)), 5, false)
		}
		fmt.Printf("Shutdown requested for %s (%s)\n", target.label, target.vmid)
	}
	return nil
}

func removeFileGo(path string) error {
	if strings.TrimSpace(path) == "" {
		return fmt.Errorf("path is required")
	}
	if _, err := os.Stat(path); os.IsNotExist(err) {
		return nil
	}
	return os.Remove(path)
}

func requireEnvKeysGo(env map[string]string, keys []string) error {
	missing := make([]string, 0)
	for _, key := range keys {
		if strings.TrimSpace(env[key]) == "" {
			missing = append(missing, key)
		}
	}
	if len(missing) != 0 {
		return fmt.Errorf("missing required environment variables: %s", strings.Join(missing, ", "))
	}
	return nil
}

func ensureTCPEndpointGo(host string, port int, label string, hint string) error {
	conn, err := net.DialTimeout("tcp", net.JoinHostPort(host, fmt.Sprintf("%d", port)), 5*time.Second)
	if err == nil {
		_ = conn.Close()
		return nil
	}
	if dnsErr := new(net.DNSError); errors.As(err, &dnsErr) {
		return fmt.Errorf("%s target %q is not resolvable from this workstation. %s\n%v", label, host, hint, err)
	}
	return fmt.Errorf("%s is not reachable at %s:%d. Connect to the required network or fix access before rerunning `haac up`.\n%v", label, host, port, err)
}

func warnSharedCredentialScopeGo(env map[string]string) {
	mainUsername := strings.TrimSpace(env["HAAC_MAIN_USERNAME"])
	downloaderUsername := strings.TrimSpace(env["QBITTORRENT_USERNAME"])
	mainPassword := strings.TrimSpace(env["HAAC_MAIN_PASSWORD"])
	downloaderPassword := strings.TrimSpace(env["QUI_PASSWORD"])
	if sharedDownloaderCredentialsEnabledGo(env) {
		fmt.Println("[warn] HAAC_ENABLE_SHARED_DOWNLOADER_CREDENTIALS is enabled: qBittorrent and QUI inherit the main operator credentials when their dedicated downloader vars are unset.")
		return
	}
	if mainUsername != "" && downloaderUsername != "" && mainUsername == downloaderUsername {
		fmt.Println("[warn] QBITTORRENT_USERNAME currently matches HAAC_MAIN_USERNAME. This widens the auth blast radius.")
	}
	if mainPassword != "" && downloaderPassword != "" && mainPassword == downloaderPassword {
		fmt.Println("[warn] QUI_PASSWORD currently matches HAAC_MAIN_PASSWORD. This widens the auth blast radius.")
	}
}

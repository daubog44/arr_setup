package cli

import (
	"archive/tar"
	"archive/zip"
	"bufio"
	"compress/gzip"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"github.com/spf13/cobra"
)

const (
	defaultWSLDistro   = "Debian"
	tofuVersion        = "1.11.5"
	helmVersion        = "4.1.3"
	kubectlVersion     = "1.35.3"
	kubesealVersion    = "0.36.1"
	taskVersion        = "3.49.1"
	ansibleCoreVersion = "2.19.1"
)

type toolInstallScope string

const (
	toolInstallScopeLocal  toolInstallScope = "local"
	toolInstallScopeGlobal toolInstallScope = "global"
)

type toolInstallOptions struct {
	workspaceRoot   string
	scope           string
	upgrade         bool
	withControlNode bool
}

func newInstallToolsCmd() *cobra.Command {
	var workspace string
	var scope string
	var upgrade bool
	var withControlNode bool

	cmd := &cobra.Command{
		Use:   "install-tools",
		Short: "Bootstrap the managed HaaC toolchain for a workspace or global user scope",
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) != 0 {
				return fmt.Errorf("install-tools does not accept extra arguments")
			}
			workspaceRoot, err := resolveWorkspaceRoot(workspace)
			if err != nil {
				return err
			}
			if !cmd.Flags().Changed("with-control-node") {
				withControlNode = true
			}
			return installTools(toolInstallOptions{
				workspaceRoot:   workspaceRoot,
				scope:           scope,
				upgrade:         upgrade,
				withControlNode: withControlNode,
			})
		},
	}
	cmd.Flags().StringVar(&workspace, "workspace", "", "Initialized HaaC workspace path (defaults to current workspace)")
	cmd.Flags().StringVar(&scope, "scope", string(toolInstallScopeLocal), "Tool install scope: local or global")
	cmd.Flags().BoolVar(&upgrade, "upgrade", false, "Force refresh of the managed tools even when the current version markers match")
	cmd.Flags().BoolVar(&withControlNode, "with-control-node", false, "Also install the managed Ansible/control-node runtime where supported")
	return cmd
}

func newUpdateToolsCmd() *cobra.Command {
	var workspace string
	var scope string
	var withControlNode bool

	cmd := &cobra.Command{
		Use:   "update-tools",
		Short: "Refresh the managed HaaC toolchain against the configured versions",
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) != 0 {
				return fmt.Errorf("update-tools does not accept extra arguments")
			}
			workspaceRoot, err := resolveWorkspaceRoot(workspace)
			if err != nil {
				return err
			}
			if !cmd.Flags().Changed("with-control-node") {
				withControlNode = true
			}
			return installTools(toolInstallOptions{
				workspaceRoot:   workspaceRoot,
				scope:           scope,
				upgrade:         false,
				withControlNode: withControlNode,
			})
		},
	}
	cmd.Flags().StringVar(&workspace, "workspace", "", "Initialized HaaC workspace path (defaults to current workspace)")
	cmd.Flags().StringVar(&scope, "scope", string(toolInstallScopeLocal), "Tool install scope: local or global")
	cmd.Flags().BoolVar(&withControlNode, "with-control-node", false, "Also install the managed Ansible/control-node runtime where supported")
	return cmd
}

func installTools(options toolInstallOptions) error {
	scope := toolInstallScope(strings.TrimSpace(options.scope))
	if scope == "" {
		scope = toolInstallScopeLocal
	}
	if scope != toolInstallScopeLocal && scope != toolInstallScopeGlobal {
		return fmt.Errorf("unsupported install scope %q; expected local or global", options.scope)
	}

	env, err := mergedEnvFromRepo(options.workspaceRoot)
	if err != nil {
		return err
	}

	targets := [][2]string{{runtime.GOOS, runtime.GOARCH}}
	if scope == toolInstallScopeLocal && runtime.GOOS == "windows" {
		wslArch, err := detectWSLArch(env)
		if err != nil {
			return err
		}
		targets = append(targets, [2]string{"linux", wslArch})
	}

	seen := map[[2]string]bool{}
	for _, target := range targets {
		if seen[target] {
			continue
		}
		seen[target] = true
		for _, tool := range []string{"tofu", "helm", "kubectl", "kubeseal", "task"} {
			installed, err := ensureScopedCLITool(options.workspaceRoot, tool, target[0], target[1], env, scope, options.upgrade)
			if err != nil {
				return err
			}
			fmt.Printf("Installed %s (%s scope) for %s-%s at %s\n", tool, scope, target[0], target[1], installed)
		}
	}

	for _, global := range []string{"python", "git", "ssh"} {
		if _, err := exec.LookPath(global); err != nil {
			return fmt.Errorf("missing required global tooling that is not bootstrapped locally: %s", global)
		}
	}

	if scope == toolInstallScopeLocal {
		if err := ensureSSHKeypair(filepath.Join(options.workspaceRoot, ".ssh", "haac_ed25519"), "haac@local"); err != nil {
			return err
		}
		if err := ensureSSHKeypair(filepath.Join(options.workspaceRoot, ".ssh", "haac_semaphore_ed25519"), "haac-semaphore@local"); err != nil {
			return err
		}
		if err := ensureSSHKeypair(filepath.Join(options.workspaceRoot, ".ssh", "haac_repo_deploy_ed25519"), "haac-repo-deploy@local"); err != nil {
			return err
		}
	}

	if options.withControlNode {
		if runtime.GOOS == "windows" {
			if err := installWSLTools(env); err != nil {
				return err
			}
		} else {
			installed, err := ensureManagedAnsible(scope, options.workspaceRoot, options.upgrade)
			if err != nil {
				return err
			}
			fmt.Printf("Installed managed ansible-playbook (%s scope) at %s\n", scope, installed)
		}
	}

	if scope == toolInstallScopeGlobal {
		globalBin, err := userGlobalBinDir()
		if err == nil {
			fmt.Printf("Global toolchain installed under %s. Ensure that directory is on PATH before invoking the binaries directly.\n", globalBin)
		}
	}
	return nil
}

func mergedEnvFromRepo(repoRoot string) (map[string]string, error) {
	merged := map[string]string{}
	for _, entry := range os.Environ() {
		key, value, ok := strings.Cut(entry, "=")
		if !ok {
			continue
		}
		merged[key] = value
	}
	envPath := filepath.Join(repoRoot, ".env")
	file, err := os.Open(envPath)
	if err == nil {
		defer file.Close()
		scanner := bufio.NewScanner(file)
		for scanner.Scan() {
			line := strings.TrimSpace(scanner.Text())
			if line == "" || strings.HasPrefix(line, "#") || !strings.Contains(line, "=") {
				continue
			}
			key, value, _ := strings.Cut(line, "=")
			key = strings.TrimSpace(key)
			value = strings.TrimSpace(value)
			if len(value) >= 2 && ((strings.HasPrefix(value, "\"") && strings.HasSuffix(value, "\"")) || (strings.HasPrefix(value, "'") && strings.HasSuffix(value, "'"))) {
				value = value[1 : len(value)-1]
			}
			if _, exists := merged[key]; !exists {
				merged[key] = value
			}
		}
		if err := scanner.Err(); err != nil {
			return nil, err
		}
	} else if !os.IsNotExist(err) {
		return nil, err
	}
	if value := strings.TrimSpace(merged["LXC_PASSWORD"]); value != "" && strings.TrimSpace(merged["PROXMOX_HOST_PASSWORD"]) == "" {
		merged["PROXMOX_HOST_PASSWORD"] = value
	}
	if err := applyIdentityDefaultsGo(merged); err != nil {
		return nil, err
	}
	if err := applyDerivedEnvDefaultsGo(repoRoot, merged); err != nil {
		return nil, err
	}
	return merged, nil
}

func detectWSLArch(env map[string]string) (string, error) {
	if _, err := exec.LookPath("wsl"); err != nil {
		return "", fmt.Errorf("WSL is not installed. Install WSL and %s first, then rerun install-tools", wslDistro(env))
	}
	output, err := runWSLOutputWithRetries(env, "uname", "-m")
	if err != nil {
		if retryableWSLRuntimeError(fmt.Sprint(err), err) {
			return "", fmt.Errorf("WSL runtime socket queue stayed saturated after retries. Close parallel WSL/tunnel sessions or run `wsl --shutdown`, then rerun doctor: %w", err)
		}
		return "", fmt.Errorf("resolve WSL architecture for distro %s: %w", wslDistro(env), err)
	}
	return normalizeArch(output)
}

func wslDistro(env map[string]string) string {
	if value := strings.TrimSpace(env["HAAC_WSL_DISTRO"]); value != "" {
		return value
	}
	return defaultWSLDistro
}

func normalizeArch(raw string) (string, error) {
	switch strings.TrimSpace(strings.ToLower(raw)) {
	case "x86_64", "amd64":
		return "amd64", nil
	case "arm64", "aarch64":
		return "arm64", nil
	default:
		return "", fmt.Errorf("unsupported architecture for local tool bootstrap: %s", strings.TrimSpace(raw))
	}
}

func repoLocalBinaryPath(repoRoot, name, goos, goarch string) string {
	binary := name
	if goos == "windows" {
		binary += ".exe"
	}
	return filepath.Join(repoRoot, ".tools", fmt.Sprintf("%s-%s", goos, goarch), "bin", binary)
}

func userGlobalBinDir() (string, error) {
	if runtime.GOOS == "windows" {
		localAppData := strings.TrimSpace(os.Getenv("LOCALAPPDATA"))
		if localAppData == "" {
			return "", fmt.Errorf("LOCALAPPDATA is required to resolve the global haac tool directory on Windows")
		}
		return filepath.Join(localAppData, "Programs", "haac", "bin"), nil
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(home, ".local", "bin"), nil
}

func userGlobalDataDir() (string, error) {
	if runtime.GOOS == "windows" {
		localAppData := strings.TrimSpace(os.Getenv("LOCALAPPDATA"))
		if localAppData == "" {
			return "", fmt.Errorf("LOCALAPPDATA is required to resolve the global haac data directory on Windows")
		}
		return filepath.Join(localAppData, "haac"), nil
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(home, ".local", "share", "haac"), nil
}

func scopedBinaryPath(repoRoot, name, goos, goarch string, scope toolInstallScope) (string, error) {
	switch scope {
	case toolInstallScopeLocal:
		return repoLocalBinaryPath(repoRoot, name, goos, goarch), nil
	case toolInstallScopeGlobal:
		globalDir, err := userGlobalBinDir()
		if err != nil {
			return "", err
		}
		return filepath.Join(globalDir, binaryNameForPlatform(name, goos)), nil
	default:
		return "", fmt.Errorf("unsupported install scope %q", scope)
	}
}

func managedAnsibleRoot(scope toolInstallScope, workspaceRoot string) (string, error) {
	switch scope {
	case toolInstallScopeLocal:
		return filepath.Join(workspaceRoot, ".tools", fmt.Sprintf("%s-%s", runtime.GOOS, runtime.GOARCH), "python"), nil
	case toolInstallScopeGlobal:
		globalDataDir, err := userGlobalDataDir()
		if err != nil {
			return "", err
		}
		return filepath.Join(globalDataDir, "python"), nil
	default:
		return "", fmt.Errorf("unsupported install scope %q", scope)
	}
}

func managedAnsibleBinary(scope toolInstallScope, workspaceRoot string) (string, error) {
	root, err := managedAnsibleRoot(scope, workspaceRoot)
	if err != nil {
		return "", err
	}
	return filepath.Join(root, "bin", "ansible-playbook"), nil
}

func ensureManagedAnsible(scope toolInstallScope, workspaceRoot string, upgrade bool) (string, error) {
	ansibleBinary, err := managedAnsibleBinary(scope, workspaceRoot)
	if err != nil {
		return "", err
	}
	versionMarker := ansibleBinary + ".version"
	if !upgrade && fileExists(ansibleBinary) {
		if data, err := os.ReadFile(versionMarker); err == nil && strings.TrimSpace(string(data)) == ansibleCoreVersion {
			return ansibleBinary, nil
		}
	}

	pythonBinary, err := resolvePythonVenvBootstrapBinary()
	if err != nil {
		return "", err
	}
	venvRoot := filepath.Dir(filepath.Dir(ansibleBinary))
	if upgrade {
		_ = os.RemoveAll(venvRoot)
	}
	if err := os.MkdirAll(filepath.Dir(venvRoot), 0o755); err != nil {
		return "", err
	}
	venvConfig := filepath.Join(venvRoot, "pyvenv.cfg")
	if !fileExists(venvConfig) {
		cmd := exec.Command(pythonBinary, "-m", "venv", venvRoot)
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		cmd.Stdin = os.Stdin
		if err := cmd.Run(); err != nil {
			return "", err
		}
	}
	pipBinary := filepath.Join(venvRoot, "bin", "pip")
	if !fileExists(pipBinary) {
		return "", fmt.Errorf("managed Python venv was created without pip at %s", pipBinary)
	}
	for _, args := range [][]string{
		{"install", "--upgrade", "pip", "setuptools", "wheel"},
		{"install", "--upgrade", fmt.Sprintf("ansible-core==%s", ansibleCoreVersion)},
	} {
		cmd := exec.Command(pipBinary, args...)
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		cmd.Stdin = os.Stdin
		if err := cmd.Run(); err != nil {
			return "", err
		}
	}
	if err := os.WriteFile(versionMarker, []byte(ansibleCoreVersion+"\n"), 0o644); err != nil {
		return "", err
	}
	return ansibleBinary, nil
}

func resolvePythonVenvBootstrapBinary() (string, error) {
	for _, candidate := range []string{"python3", "python"} {
		if resolved, err := exec.LookPath(candidate); err == nil {
			return resolved, nil
		}
	}
	return "", fmt.Errorf("python3 or python is required to bootstrap the managed ansible runtime")
}

func findManagedAnsibleBinary(repoRoot string) string {
	for _, scope := range []toolInstallScope{toolInstallScopeLocal, toolInstallScopeGlobal} {
		ansibleBinary, err := managedAnsibleBinary(scope, repoRoot)
		if err != nil {
			continue
		}
		if fileExists(ansibleBinary) {
			return ansibleBinary
		}
	}
	return ""
}

func ensureScopedCLITool(repoRoot, name, goos, goarch string, env map[string]string, scope toolInstallScope, upgrade bool) (string, error) {
	destination, err := scopedBinaryPath(repoRoot, name, goos, goarch, scope)
	if err != nil {
		return "", err
	}
	return ensureManagedCLITool(destination, name, goos, goarch, requestedToolVersion(name, env), upgrade)
}

func ensureManagedCLITool(destination, name, goos, goarch, requestedVersion string, upgrade bool) (string, error) {
	versionMarker := destination + ".version"
	if !upgrade {
		if info, err := os.Stat(destination); err == nil && !info.IsDir() {
			if data, err := os.ReadFile(versionMarker); err == nil {
				if strings.TrimSpace(string(data)) == requestedVersion {
					return destination, nil
				}
			} else if os.IsNotExist(err) {
				if err := os.WriteFile(versionMarker, []byte(requestedVersion+"\n"), 0o644); err == nil {
					return destination, nil
				}
			}
		}
	}
	if err := os.MkdirAll(filepath.Dir(destination), 0o755); err != nil {
		return "", err
	}

	switch name {
	case "tofu":
		extension := "tar.gz"
		if goos == "windows" {
			extension = "zip"
		}
		url := fmt.Sprintf("https://github.com/opentofu/opentofu/releases/download/v%s/tofu_%s_%s_%s.%s", requestedVersion, requestedVersion, goos, goarch, extension)
		if goos == "windows" {
			if err := installZipBinary(url, map[string]string{"tofu.exe": destination}); err != nil {
				return "", err
			}
		} else if err := installTarGzBinary(url, map[string]string{"tofu": destination}, goos); err != nil {
			return "", err
		}
	case "helm":
		if goos == "windows" {
			url := fmt.Sprintf("https://get.helm.sh/helm-v%s-windows-%s.zip", requestedVersion, goarch)
			if err := installZipBinary(url, map[string]string{fmt.Sprintf("windows-%s/helm.exe", goarch): destination}); err != nil {
				return "", err
			}
		} else {
			url := fmt.Sprintf("https://get.helm.sh/helm-v%s-%s-%s.tar.gz", requestedVersion, goos, goarch)
			if err := installTarGzBinary(url, map[string]string{fmt.Sprintf("%s-%s/helm", goos, goarch): destination}, goos); err != nil {
				return "", err
			}
		}
	case "kubectl":
		url := fmt.Sprintf("https://dl.k8s.io/release/v%s/bin/%s/%s/%s", requestedVersion, goos, goarch, binaryNameForPlatform("kubectl", goos))
		if err := installDirectBinary(url, destination, goos); err != nil {
			return "", err
		}
	case "kubeseal":
		url := fmt.Sprintf("https://github.com/bitnami-labs/sealed-secrets/releases/download/v%s/kubeseal-%s-%s-%s.tar.gz", requestedVersion, requestedVersion, goos, goarch)
		if err := installTarGzBinary(url, map[string]string{binaryNameForPlatform("kubeseal", goos): destination}, goos); err != nil {
			return "", err
		}
	case "task":
		if goos == "windows" {
			url := fmt.Sprintf("https://github.com/go-task/task/releases/download/v%s/task_windows_%s.zip", requestedVersion, goarch)
			if err := installZipBinary(url, map[string]string{"task.exe": destination}); err != nil {
				return "", err
			}
		} else {
			url := fmt.Sprintf("https://github.com/go-task/task/releases/download/v%s/task_%s_%s.tar.gz", requestedVersion, goos, goarch)
			if err := installTarGzBinary(url, map[string]string{"task": destination}, goos); err != nil {
				return "", err
			}
		}
	default:
		return "", fmt.Errorf("unsupported local tool bootstrap: %s", name)
	}

	if err := os.WriteFile(versionMarker, []byte(requestedVersion+"\n"), 0o644); err != nil {
		return "", err
	}
	return destination, nil
}

func ensureLocalCLITool(repoRoot, name, goos, goarch string, env map[string]string) (string, error) {
	return ensureScopedCLITool(repoRoot, name, goos, goarch, env, toolInstallScopeLocal, false)
}

func requestedToolVersion(name string, env map[string]string) string {
	switch name {
	case "tofu":
		return firstNonEmpty(env["HAAC_TOFU_VERSION"], tofuVersion)
	case "helm":
		return firstNonEmpty(env["HAAC_HELM_VERSION"], helmVersion)
	case "kubectl":
		return firstNonEmpty(env["HAAC_KUBECTL_VERSION"], kubectlVersion)
	case "kubeseal":
		return firstNonEmpty(env["HAAC_KUBESEAL_VERSION"], kubesealVersion)
	case "task":
		return firstNonEmpty(env["HAAC_TASK_VERSION"], taskVersion)
	default:
		return ""
	}
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return strings.TrimSpace(value)
		}
	}
	return ""
}

func binaryNameForPlatform(name, goos string) string {
	if goos == "windows" {
		return name + ".exe"
	}
	return name
}

func installDirectBinary(url, destination, goos string) error {
	resp, err := http.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("download %s failed: HTTP %d", url, resp.StatusCode)
	}
	file, stagedPath, err := createStagedBinary(destination)
	if err != nil {
		return err
	}
	defer os.Remove(stagedPath)
	defer file.Close()
	if _, err := io.Copy(file, resp.Body); err != nil {
		return err
	}
	if err := file.Close(); err != nil {
		return err
	}
	return commitStagedBinary(stagedPath, destination, goos)
}

func installZipBinary(url string, members map[string]string) error {
	archivePath, err := downloadTempFile(url, ".zip")
	if err != nil {
		return err
	}
	defer os.Remove(archivePath)

	reader, err := zip.OpenReader(archivePath)
	if err != nil {
		return err
	}
	defer reader.Close()

	for _, file := range reader.File {
		target, ok := members[file.Name]
		if !ok {
			continue
		}
		if err := writeZipMember(file, target); err != nil {
			return err
		}
	}
	for member, target := range members {
		if _, err := os.Stat(target); err != nil {
			return fmt.Errorf("archive entry not found after extraction: %s", member)
		}
	}
	return nil
}

func writeZipMember(file *zip.File, target string) error {
	reader, err := file.Open()
	if err != nil {
		return err
	}
	defer reader.Close()
	output, stagedPath, err := createStagedBinary(target)
	if err != nil {
		return err
	}
	defer os.Remove(stagedPath)
	defer output.Close()
	if _, err := io.Copy(output, reader); err != nil {
		return err
	}
	if err := output.Close(); err != nil {
		return err
	}
	return commitStagedBinary(stagedPath, target, targetPlatformForBinary(target))
}

func installTarGzBinary(url string, members map[string]string, goos string) error {
	archivePath, err := downloadTempFile(url, ".tar.gz")
	if err != nil {
		return err
	}
	defer os.Remove(archivePath)

	file, err := os.Open(archivePath)
	if err != nil {
		return err
	}
	defer file.Close()

	gzipReader, err := gzip.NewReader(file)
	if err != nil {
		return err
	}
	defer gzipReader.Close()

	tarReader := tar.NewReader(gzipReader)
	for {
		header, err := tarReader.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			return err
		}
		target, ok := members[header.Name]
		if !ok {
			continue
		}
		output, stagedPath, err := createStagedBinary(target)
		if err != nil {
			return err
		}
		defer os.Remove(stagedPath)
		if _, err := io.Copy(output, tarReader); err != nil {
			output.Close()
			return err
		}
		if err := output.Close(); err != nil {
			return err
		}
		if err := commitStagedBinary(stagedPath, target, goos); err != nil {
			return err
		}
	}

	for member, target := range members {
		if _, err := os.Stat(target); err != nil {
			return fmt.Errorf("archive entry not found after extraction: %s", member)
		}
	}
	return nil
}

func downloadTempFile(url, suffix string) (string, error) {
	resp, err := http.Get(url)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return "", fmt.Errorf("download %s failed: HTTP %d", url, resp.StatusCode)
	}
	file, err := os.CreateTemp("", "haac-*"+suffix)
	if err != nil {
		return "", err
	}
	defer file.Close()
	if _, err := io.Copy(file, resp.Body); err != nil {
		return "", err
	}
	return file.Name(), nil
}

func ensureExecutable(path, goos string) error {
	if goos == "windows" {
		return nil
	}
	return os.Chmod(path, 0o755)
}

func createStagedBinary(target string) (*os.File, string, error) {
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		return nil, "", err
	}
	file, err := os.CreateTemp(filepath.Dir(target), ".haac-stage-*")
	if err != nil {
		return nil, "", err
	}
	return file, file.Name(), nil
}

func targetPlatformForBinary(path string) string {
	if strings.HasSuffix(strings.ToLower(path), ".exe") {
		return "windows"
	}
	return runtime.GOOS
}

func commitStagedBinary(stagedPath, destination, goos string) error {
	if err := ensureExecutable(stagedPath, goos); err != nil {
		return err
	}
	var lastErr error
	for attempt := 0; attempt < 10; attempt++ {
		if err := os.Remove(destination); err != nil && !os.IsNotExist(err) {
			lastErr = err
			time.Sleep(500 * time.Millisecond)
			continue
		}
		if err := os.Rename(stagedPath, destination); err != nil {
			lastErr = err
			time.Sleep(500 * time.Millisecond)
			continue
		}
		return nil
	}
	if lastErr == nil {
		lastErr = fmt.Errorf("unknown replacement failure")
	}
	return fmt.Errorf("replace managed binary %s: %w. Close any process using that tool and rerun the command", destination, lastErr)
}

func ensureSSHKeypair(privateKeyPath, comment string) error {
	publicKeyPath := privateKeyPath + ".pub"
	if fileExists(privateKeyPath) && fileExists(publicKeyPath) {
		return nil
	}
	sshKeygen, err := exec.LookPath("ssh-keygen")
	if err != nil {
		return fmt.Errorf("ssh-keygen is required to create the repository SSH keypair")
	}
	if err := os.MkdirAll(filepath.Dir(privateKeyPath), 0o755); err != nil {
		return err
	}
	cmd := exec.Command(sshKeygen, "-t", "ed25519", "-f", privateKeyPath, "-N", "", "-C", comment)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin
	return cmd.Run()
}

func installWSLTools(env map[string]string) error {
	if _, err := exec.LookPath("wsl"); err != nil {
		return fmt.Errorf("WSL is not installed. Install WSL and %s first, then rerun this command", wslDistro(env))
	}
	if !wslDistroExists(env) {
		return fmt.Errorf("WSL distro %q was not found. Install it first, then rerun this command", wslDistro(env))
	}
	cmd := exec.Command(
		"wsl", "-d", wslDistro(env), "-u", "root", "--",
		"bash", "-lc",
		"apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y ansible git python3 python3-venv openssh-client",
	)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin
	return cmd.Run()
}

func wslDistroExists(env map[string]string) bool {
	cmd := exec.Command("wsl", "-l", "-q")
	output, err := cmd.Output()
	if err != nil {
		return false
	}
	for _, line := range strings.Split(strings.ReplaceAll(string(output), "\x00", ""), "\n") {
		if strings.TrimSpace(line) == wslDistro(env) {
			return true
		}
	}
	return false
}

func runWSLOutputWithRetries(env map[string]string, args ...string) (string, error) {
	var lastOutput string
	var lastErr error
	commandArgs := append([]string{"-d", wslDistro(env), "--"}, args...)
	for attempt := 1; attempt <= 5; attempt++ {
		cmd := exec.Command("wsl", commandArgs...)
		output, err := cmd.CombinedOutput()
		cleaned := strings.TrimSpace(strings.ReplaceAll(string(output), "\x00", ""))
		if err == nil {
			return cleaned, nil
		}
		lastOutput = cleaned
		lastErr = err
		if !retryableWSLRuntimeError(cleaned, err) {
			break
		}
		time.Sleep(time.Duration(attempt) * time.Second)
	}
	if lastOutput != "" {
		return "", fmt.Errorf("%w: %s", lastErr, lastOutput)
	}
	return "", lastErr
}

func retryableWSLRuntimeError(output string, err error) bool {
	if err == nil {
		return false
	}
	lowered := strings.ToLower(output)
	return strings.Contains(lowered, "0x80072747") ||
		strings.Contains(lowered, "buffer") ||
		strings.Contains(lowered, "coda piena") ||
		strings.Contains(lowered, "socket")
}

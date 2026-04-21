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

	"github.com/spf13/cobra"
)

const (
	defaultWSLDistro  = "Debian"
	tofuVersion       = "1.11.5"
	helmVersion       = "4.1.3"
	kubectlVersion    = "1.35.3"
	kubesealVersion   = "0.36.1"
	taskVersion       = "3.49.1"
)

func newInstallToolsCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "install-tools",
		Short: "Bootstrap the repo-local portable toolchain and required local keys",
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) != 0 {
				return fmt.Errorf("install-tools does not accept extra arguments")
			}
			b, err := newBridge()
			if err != nil {
				return err
			}
			return installTools(b.repoRoot)
		},
	}
}

func installTools(repoRoot string) error {
	env, err := mergedEnvFromRepo(repoRoot)
	if err != nil {
		return err
	}

	targets := [][2]string{{runtime.GOOS, runtime.GOARCH}}
	if runtime.GOOS == "windows" {
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
			installed, err := ensureLocalCLITool(repoRoot, tool, target[0], target[1], env)
			if err != nil {
				return err
			}
			fmt.Printf("Installed portable %s for %s-%s at %s\n", tool, target[0], target[1], installed)
		}
	}

	for _, global := range []string{"python", "git", "ssh"} {
		if _, err := exec.LookPath(global); err != nil {
			return fmt.Errorf("missing required global tooling that is not bootstrapped locally: %s", global)
		}
	}

	if err := ensureSSHKeypair(filepath.Join(repoRoot, ".ssh", "haac_ed25519"), "haac@local"); err != nil {
		return err
	}
	if err := ensureSSHKeypair(filepath.Join(repoRoot, ".ssh", "haac_semaphore_ed25519"), "haac-semaphore@local"); err != nil {
		return err
	}
	if err := ensureSSHKeypair(filepath.Join(repoRoot, ".ssh", "haac_repo_deploy_ed25519"), "haac-repo-deploy@local"); err != nil {
		return err
	}

	if runtime.GOOS == "windows" {
		if err := installWSLTools(env); err != nil {
			return err
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
	return merged, nil
}

func detectWSLArch(env map[string]string) (string, error) {
	if _, err := exec.LookPath("wsl"); err != nil {
		return "", fmt.Errorf("WSL is not installed. Install WSL and %s first, then rerun install-tools", wslDistro(env))
	}
	cmd := exec.Command("wsl", "-d", wslDistro(env), "--", "uname", "-m")
	output, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("resolve WSL architecture for distro %s: %w", wslDistro(env), err)
	}
	return normalizeArch(string(output))
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

func ensureLocalCLITool(repoRoot, name, goos, goarch string, env map[string]string) (string, error) {
	destination := repoLocalBinaryPath(repoRoot, name, goos, goarch)
	requestedVersion := requestedToolVersion(name, env)
	versionMarker := destination + ".version"
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
	file, err := os.Create(destination)
	if err != nil {
		return err
	}
	defer file.Close()
	if _, err := io.Copy(file, resp.Body); err != nil {
		return err
	}
	return ensureExecutable(destination, goos)
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
	output, err := os.Create(target)
	if err != nil {
		return err
	}
	defer output.Close()
	if _, err := io.Copy(output, reader); err != nil {
		return err
	}
	if strings.HasSuffix(strings.ToLower(target), ".exe") {
		return nil
	}
	return os.Chmod(target, 0o755)
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
		output, err := os.Create(target)
		if err != nil {
			return err
		}
		if _, err := io.Copy(output, tarReader); err != nil {
			output.Close()
			return err
		}
		output.Close()
		if err := ensureExecutable(target, goos); err != nil {
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
		"apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y ansible git python3 openssh-client sshpass",
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

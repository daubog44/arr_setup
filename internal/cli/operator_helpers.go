package cli

import (
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"os/exec"
	pathpkg "path"
	"path/filepath"
	"regexp"
	"runtime"
	"strconv"
	"strings"
	"time"
)

var (
	safeUsernamePattern    = regexp.MustCompile(`^[A-Za-z0-9._-]+$`)
	safeInlineValuePattern = regexp.MustCompile(`^[^\r\n"]+$`)
)

func applyIdentityDefaultsGo(env map[string]string) error {
	mainUsername := envValueGo(env, "HAAC_MAIN_USERNAME")
	mainPassword := envValueGo(env, "HAAC_MAIN_PASSWORD")
	mainEmail := envValueGo(env, "HAAC_MAIN_EMAIL")
	mainName := envValueGo(env, "HAAC_MAIN_NAME")

	if mainUsername != "" {
		for _, key := range []string{
			"AUTHELIA_ADMIN_USERNAME",
			"ARGOCD_USERNAME",
			"BAZARR_AUTH_USERNAME",
			"GRAFANA_ADMIN_USERNAME",
			"JELLYFIN_ADMIN_USERNAME",
			"LITMUS_ADMIN_USERNAME",
			"SEMAPHORE_ADMIN_USERNAME",
		} {
			setDefaultGo(env, key, mainUsername)
		}
	}
	if mainPassword != "" {
		for _, key := range []string{
			"AUTHELIA_ADMIN_PASSWORD",
			"ARGOCD_PASSWORD",
			"BAZARR_AUTH_PASSWORD",
			"GRAFANA_ADMIN_PASSWORD",
			"JELLYFIN_ADMIN_PASSWORD",
			"LITMUS_ADMIN_PASSWORD",
			"SEMAPHORE_ADMIN_PASSWORD",
		} {
			setDefaultGo(env, key, mainPassword)
		}
	}

	setDefaultGo(env, "AUTHELIA_ADMIN_USERNAME", "admin")
	autheliaUsername := envValueGo(env, "AUTHELIA_ADMIN_USERNAME")
	if autheliaUsername == "" {
		autheliaUsername = "admin"
	}
	for _, key := range []string{"ARGOCD_USERNAME", "BAZARR_AUTH_USERNAME", "GRAFANA_ADMIN_USERNAME", "LITMUS_ADMIN_USERNAME", "SEMAPHORE_ADMIN_USERNAME"} {
		setDefaultGo(env, key, autheliaUsername)
	}
	if envValueGo(env, "AUTHELIA_ADMIN_PASSWORD") != "" {
		for _, key := range []string{"ARGOCD_PASSWORD", "BAZARR_AUTH_PASSWORD", "GRAFANA_ADMIN_PASSWORD", "LITMUS_ADMIN_PASSWORD", "SEMAPHORE_ADMIN_PASSWORD"} {
			setDefaultGo(env, key, envValueGo(env, "AUTHELIA_ADMIN_PASSWORD"))
		}
	}

	if mainEmail != "" {
		setDefaultGo(env, "AUTHELIA_ADMIN_EMAIL", mainEmail)
		setDefaultGo(env, "JELLYFIN_ADMIN_EMAIL", mainEmail)
		setDefaultGo(env, "SEMAPHORE_ADMIN_EMAIL", mainEmail)
	}
	domainName := envValueGo(env, "DOMAIN_NAME")
	if domainName != "" {
		setDefaultGo(env, "AUTHELIA_ADMIN_EMAIL", fmt.Sprintf("%s@%s", autheliaUsername, domainName))
		setDefaultGo(env, "JELLYFIN_ADMIN_EMAIL", fmt.Sprintf("%s@%s", autheliaUsername, domainName))
		setDefaultGo(env, "SEMAPHORE_ADMIN_EMAIL", fmt.Sprintf("%s@%s", autheliaUsername, domainName))
	}
	setDefaultGo(env, "SEMAPHORE_ADMIN_EMAIL", "admin@localhost")

	if mainName != "" {
		setDefaultGo(env, "AUTHELIA_ADMIN_NAME", mainName)
		setDefaultGo(env, "SEMAPHORE_ADMIN_NAME", mainName)
	}
	setDefaultGo(env, "AUTHELIA_ADMIN_NAME", "Administrator")
	setDefaultGo(env, "SEMAPHORE_ADMIN_NAME", envValueGo(env, "AUTHELIA_ADMIN_NAME"))

	if sharedDownloaderCredentialsEnabledGo(env) {
		setDefaultGo(env, "QBITTORRENT_USERNAME", mainUsername)
		setDefaultGo(env, "QUI_PASSWORD", mainPassword)
	}

	for _, pair := range []struct {
		key     string
		pattern *regexp.Regexp
		hint    string
	}{
		{"HAAC_MAIN_USERNAME", safeUsernamePattern, "Use only letters, digits, dot, underscore, or dash."},
		{"AUTHELIA_ADMIN_USERNAME", safeUsernamePattern, "Use only letters, digits, dot, underscore, or dash."},
		{"ARGOCD_USERNAME", safeUsernamePattern, "Use only letters, digits, dot, underscore, or dash."},
		{"BAZARR_AUTH_USERNAME", safeUsernamePattern, "Use only letters, digits, dot, underscore, or dash."},
		{"GRAFANA_ADMIN_USERNAME", safeUsernamePattern, "Use only letters, digits, dot, underscore, or dash."},
		{"JELLYFIN_ADMIN_USERNAME", safeUsernamePattern, "Use only letters, digits, dot, underscore, or dash."},
		{"LITMUS_ADMIN_USERNAME", safeUsernamePattern, "Use only letters, digits, dot, underscore, or dash."},
		{"SEMAPHORE_ADMIN_USERNAME", safeUsernamePattern, "Use only letters, digits, dot, underscore, or dash."},
		{"QBITTORRENT_USERNAME", safeUsernamePattern, "Use only letters, digits, dot, underscore, or dash."},
		{"HAAC_MAIN_NAME", safeInlineValuePattern, "Double quotes and line breaks are not supported here."},
		{"AUTHELIA_ADMIN_NAME", safeInlineValuePattern, "Double quotes and line breaks are not supported here."},
		{"SEMAPHORE_ADMIN_NAME", safeInlineValuePattern, "Double quotes and line breaks are not supported here."},
		{"AUTHELIA_ADMIN_EMAIL", safeInlineValuePattern, "Double quotes and line breaks are not supported here."},
		{"JELLYFIN_ADMIN_EMAIL", safeInlineValuePattern, "Double quotes and line breaks are not supported here."},
		{"SEMAPHORE_ADMIN_EMAIL", safeInlineValuePattern, "Double quotes and line breaks are not supported here."},
	} {
		value := envValueGo(env, pair.key)
		if value == "" {
			continue
		}
		if !pair.pattern.MatchString(value) {
			return fmt.Errorf("%s contains unsupported characters. %s", pair.key, pair.hint)
		}
	}
	return nil
}

func envValueGo(env map[string]string, key string) string {
	return strings.TrimSpace(env[key])
}

func setDefaultGo(env map[string]string, key, value string) {
	if strings.TrimSpace(value) != "" && strings.TrimSpace(env[key]) == "" {
		env[key] = strings.TrimSpace(value)
	}
}

func sharedDownloaderCredentialsEnabledGo(env map[string]string) bool {
	switch strings.ToLower(strings.TrimSpace(env["HAAC_ENABLE_SHARED_DOWNLOADER_CREDENTIALS"])) {
	case "1", "true", "yes", "on":
		return true
	default:
		return false
	}
}

func ensureKnownHostsPathGo(repoRoot string, env map[string]string) string {
	override := strings.TrimSpace(env["HAAC_SSH_KNOWN_HOSTS_PATH"])
	path := override
	if path == "" {
		path = filepath.Join(repoRoot, ".ssh", "known_hosts")
	} else if !filepath.IsAbs(path) {
		path = filepath.Join(repoRoot, filepath.FromSlash(path))
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		panic(err)
	}
	if !fileExists(path) {
		_ = os.WriteFile(path, []byte(""), 0o600)
	}
	return path
}

func sshHostKeyCheckingModeGo(env map[string]string) string {
	switch strings.ToLower(strings.TrimSpace(env["HAAC_SSH_HOST_KEY_CHECKING"])) {
	case "accept-new", "yes", "no":
		return strings.ToLower(strings.TrimSpace(env["HAAC_SSH_HOST_KEY_CHECKING"]))
	default:
		return "accept-new"
	}
}

func sshCommonOptionsGo(repoRoot string, env map[string]string, connectTimeout int, knownHostsFile string) []string {
	if strings.TrimSpace(knownHostsFile) == "" {
		knownHostsFile = ensureKnownHostsPathGo(repoRoot, env)
	}
	return []string{
		"-o", "StrictHostKeyChecking=" + sshHostKeyCheckingModeGo(env),
		"-o", "UserKnownHostsFile=" + knownHostsFile,
		"-o", "BatchMode=yes",
		"-o", fmt.Sprintf("ConnectTimeout=%d", connectTimeout),
		"-o", "ConnectionAttempts=1",
	}
}

func proxmoxSSHCommandGo(repoRoot string, env map[string]string, host, remoteCommand string, connectTimeout int) ([]string, func(), error) {
	repoKey := filepath.Join(repoRoot, ".ssh", "haac_ed25519")
	if !fileExists(repoKey) {
		return nil, nil, fmt.Errorf("repo SSH keypair not found: %s", repoKey)
	}
	if runtime.GOOS == "windows" {
		privateKeyWSL, cleanup, err := ensureWSLSSHKeypairGo(repoRoot, env)
		if err != nil {
			return nil, nil, err
		}
		knownHostsWSL, cleanupKnownHosts, err := ensureWSLKnownHostsGo(repoRoot, env)
		if err != nil {
			cleanup()
			return nil, nil, err
		}
		sshCommand := []string{
			"ssh",
			"-o", "StrictHostKeyChecking=" + sshHostKeyCheckingModeGo(env),
			"-o", "UserKnownHostsFile=" + knownHostsWSL,
			"-o", "BatchMode=yes",
			"-o", fmt.Sprintf("ConnectTimeout=%d", connectTimeout),
			"-o", "ConnectionAttempts=1",
			"-o", "IdentitiesOnly=yes",
			"-i", privateKeyWSL,
			fmt.Sprintf("root@%s", host),
			remoteCommand,
		}
		command := []string{"wsl", "-d", wslDistro(env), "--", "bash", "-lc", "exec " + shellJoin(sshCommand)}
		return command, func() {
			cleanupKnownHosts()
			cleanup()
		}, nil
	}
	command := []string{"ssh"}
	command = append(command, sshCommonOptionsGo(repoRoot, env, connectTimeout, "")...)
	command = append(command, "-o", "IdentitiesOnly=yes", "-i", repoKey, fmt.Sprintf("root@%s", host), remoteCommand)
	return command, func() {}, nil
}

func runProxmoxSSHStdoutGo(env map[string]string, host, remoteCommand string, connectTimeout int, check bool) (string, error) {
	b, err := newBridge()
	if err != nil {
		return "", err
	}
	command, cleanup, err := proxmoxSSHCommandGo(b.repoRoot, env, host, remoteCommand, connectTimeout)
	if err != nil {
		return "", err
	}
	defer cleanup()
	cmd := exec.Command(command[0], command[1:]...)
	cmd.Dir = b.repoRoot
	cmd.Env = os.Environ()
	output, err := cmd.CombinedOutput()
	if err != nil && check {
		return "", fmt.Errorf("command failed: %s\n%s", shellJoin(command), strings.TrimSpace(string(output)))
	}
	return strings.TrimSpace(string(output)), nil
}

func clusterNodeHostsGo(env map[string]string) []string {
	hosts := make([]string, 0)
	if master := stripIPCIDRGo(env["K3S_MASTER_IP"]); master != "" {
		hosts = append(hosts, master)
	}
	raw := strings.TrimSpace(env["WORKER_NODES_JSON"])
	if raw == "" {
		return hosts
	}
	var decoded any
	if err := json.Unmarshal([]byte(raw), &decoded); err != nil {
		return hosts
	}
	switch values := decoded.(type) {
	case map[string]any:
		for _, rawValue := range values {
			if entry, ok := rawValue.(map[string]any); ok {
				if ip := stripIPCIDRGo(fmt.Sprint(entry["ip"])); ip != "" && ip != "<nil>" {
					hosts = append(hosts, ip)
				}
			}
		}
	case []any:
		for _, rawValue := range values {
			if entry, ok := rawValue.(map[string]any); ok {
				if ip := stripIPCIDRGo(fmt.Sprint(entry["ip"])); ip != "" && ip != "<nil>" {
					hosts = append(hosts, ip)
				}
			}
		}
	}
	return hosts
}

func refreshClusterKnownHostsGo(repoRoot string, env map[string]string, timeout time.Duration) error {
	accessHost := proxmoxAccessHostGo(env)
	knownHosts := ensureKnownHostsPathGo(repoRoot, env)
	for _, host := range clusterNodeHostsGo(env) {
		deadline := time.Now().Add(timeout)
		for {
			output, err := runProxmoxSSHStdoutGo(env, accessHost, fmt.Sprintf("ssh-keyscan -T 5 -t ed25519 %s 2>/dev/null || true", shellEscape(host)), 10, false)
			if err == nil && strings.TrimSpace(output) != "" {
				if err := replaceKnownHostEntriesGo(knownHosts, host, output); err != nil {
					return err
				}
				break
			}
			if time.Now().After(deadline) {
				return fmt.Errorf("timed out refreshing SSH host key for K3s node %s", host)
			}
			time.Sleep(2 * time.Second)
		}
	}
	return nil
}

func replaceKnownHostEntriesGo(path, host, entries string) error {
	existing := make([]string, 0)
	if fileExists(path) {
		data, err := readFileWithRetryGo(path)
		if err != nil {
			return err
		}
		existing = strings.Split(strings.ReplaceAll(string(data), "\r\n", "\n"), "\n")
	}
	retained := make([]string, 0, len(existing))
	for _, line := range existing {
		if line == "" || strings.HasPrefix(line, "#") {
			retained = append(retained, line)
			continue
		}
		marker := strings.SplitN(line, " ", 2)[0]
		if strings.HasPrefix(marker, "|1|") {
			retained = append(retained, line)
			continue
		}
		knownMarkers := strings.Split(marker, ",")
		skip := false
		for _, candidate := range knownMarkers {
			if candidate == host || candidate == fmt.Sprintf("[%s]:22", host) {
				skip = true
				break
			}
		}
		if !skip {
			retained = append(retained, line)
		}
	}
	for _, line := range strings.Split(entries, "\n") {
		cleaned := strings.TrimSpace(line)
		if cleaned != "" {
			retained = append(retained, cleaned)
		}
	}
	rendered := strings.Join(retained, "\n")
	if strings.TrimSpace(rendered) != "" {
		rendered += "\n"
	}
	return writeFileWithRetryGo(path, []byte(rendered), 0o600)
}

func readFileWithRetryGo(path string) ([]byte, error) {
	var data []byte
	err := withTransientFileRetryGo(func() error {
		var err error
		data, err = os.ReadFile(path)
		return err
	})
	return data, err
}

func writeFileWithRetryGo(path string, data []byte, perm fs.FileMode) error {
	return withTransientFileRetryGo(func() error {
		return os.WriteFile(path, data, perm)
	})
}

func withTransientFileRetryGo(operation func() error) error {
	var err error
	for attempt := 0; attempt < 12; attempt++ {
		err = operation()
		if err == nil || !transientFileLockErrorGo(err) {
			return err
		}
		time.Sleep(time.Duration(250+attempt*250) * time.Millisecond)
	}
	return err
}

func transientFileLockErrorGo(err error) bool {
	if err == nil {
		return false
	}
	message := strings.ToLower(err.Error())
	return strings.Contains(message, "user-mapped section open") ||
		strings.Contains(message, "being used by another process") ||
		strings.Contains(message, "sharing violation") ||
		strings.Contains(message, "access is denied")
}

func wslRuntimeDir(env map[string]string) string {
	root := strings.TrimSpace(env["HAAC_WSL_RUNTIME_ROOT"])
	if root == "" {
		root = "/tmp/haac-runtime"
	}
	runtimeID := strings.TrimSpace(env["HAAC_WSL_RUNTIME_ID"])
	if runtimeID == "" {
		runtimeID = fmt.Sprintf("pid-%d", os.Getpid())
	}
	return fmt.Sprintf("%s/%s/%s", strings.TrimRight(root, "/"), wslDistro(env), runtimeID)
}

func toPosixWSLPathGo(env map[string]string, path string) (string, error) {
	nativePath := filepath.Clean(path)
	if runtime.GOOS == "windows" {
		nativePath = strings.ReplaceAll(nativePath, `\`, "/")
	}
	cmd := exec.Command("wsl", "-d", wslDistro(env), "--", "wslpath", "-a", nativePath)
	output, err := cmd.Output()
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(output)), nil
}

func ensureWSLRuntimeDirGo(env map[string]string) (string, error) {
	runtimeDir := wslRuntimeDir(env)
	cmd := exec.Command("wsl", "-d", wslDistro(env), "--", "bash", "-lc", fmt.Sprintf("mkdir -p %s && chmod 700 %s", shellEscape(runtimeDir), shellEscape(runtimeDir)))
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return "", err
	}
	return runtimeDir, nil
}

func ensureWSLSSHKeypairGo(repoRoot string, env map[string]string) (string, func(), error) {
	privateKey := filepath.Join(repoRoot, ".ssh", "haac_ed25519")
	publicKey := privateKey + ".pub"
	if !fileExists(privateKey) || !fileExists(publicKey) {
		return "", nil, fmt.Errorf("repo SSH keypair not found: %s", privateKey)
	}
	runtimeDir, err := ensureWSLRuntimeDirGo(env)
	if err != nil {
		return "", nil, err
	}
	privateKeyWSL := pathpkg.Join(runtimeDir, "haac_ed25519")
	privateKeySourceWSL, err := toPosixWSLPathGo(env, privateKey)
	if err != nil {
		return "", nil, err
	}
	publicKeySourceWSL, err := toPosixWSLPathGo(env, publicKey)
	if err != nil {
		return "", nil, err
	}
	command := fmt.Sprintf(
		"rm -f %s %s.pub && cp -f %s %s && cp -f %s %s.pub && chmod 600 %s && chmod 644 %s.pub",
		shellEscape(privateKeyWSL), shellEscape(privateKeyWSL),
		shellEscape(privateKeySourceWSL), shellEscape(privateKeyWSL),
		shellEscape(publicKeySourceWSL), shellEscape(privateKeyWSL),
		shellEscape(privateKeyWSL), shellEscape(privateKeyWSL),
	)
	cmd := exec.Command("wsl", "-d", wslDistro(env), "--", "bash", "-lc", command)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return "", nil, err
	}
	return privateKeyWSL, func() { cleanupWSLRuntimeGo(env) }, nil
}

func ensureWSLKnownHostsGo(repoRoot string, env map[string]string) (string, func(), error) {
	localKnownHosts := ensureKnownHostsPathGo(repoRoot, env)
	runtimeDir, err := ensureWSLRuntimeDirGo(env)
	if err != nil {
		return "", nil, err
	}
	knownHostsWSL := pathpkg.Join(runtimeDir, "haac_known_hosts")
	localKnownHostsWSL, err := toPosixWSLPathGo(env, localKnownHosts)
	if err != nil {
		return "", nil, err
	}
	command := fmt.Sprintf("rm -f %s && cp -f %s %s && chmod 600 %s", shellEscape(knownHostsWSL), shellEscape(localKnownHostsWSL), shellEscape(knownHostsWSL), shellEscape(knownHostsWSL))
	cmd := exec.Command("wsl", "-d", wslDistro(env), "--", "bash", "-lc", command)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return "", nil, err
	}
	return knownHostsWSL, func() {
		syncWSLKnownHostsBackGo(repoRoot, env, knownHostsWSL)
	}, nil
}

func syncWSLKnownHostsBackGo(repoRoot string, env map[string]string, knownHostsWSL string) {
	localKnownHosts := ensureKnownHostsPathGo(repoRoot, env)
	localKnownHostsWSL, err := toPosixWSLPathGo(env, localKnownHosts)
	if err != nil {
		return
	}
	command := fmt.Sprintf("if [ -f %s ]; then cp %s %s && chmod 600 %s; fi", shellEscape(knownHostsWSL), shellEscape(knownHostsWSL), shellEscape(localKnownHostsWSL), shellEscape(localKnownHostsWSL))
	cmd := exec.Command("wsl", "-d", wslDistro(env), "--", "bash", "-lc", command)
	_ = cmd.Run()
}

func cleanupWSLRuntimeGo(env map[string]string) {
	runtimeDir := wslRuntimeDir(env)
	if runtimeDir == "" {
		return
	}
	cmd := exec.Command("wsl", "-d", wslDistro(env), "--", "bash", "-lc", fmt.Sprintf("rm -rf %s", shellEscape(runtimeDir)))
	_ = cmd.Run()
}

func ansibleEnvGo(repoRoot string, env map[string]string, privateKeyPath string, knownHostsPath string) []string {
	mapped := os.Environ()
	overrides := map[string]string{
		"HAAC_KUBECONFIG_PATH":       localKubeconfigPathGo(),
		"HAAC_SSH_PRIVATE_KEY_PATH":  privateKeyPath,
		"HAAC_SSH_KNOWN_HOSTS_PATH":  knownHostsPath,
		"HAAC_SSH_HOST_KEY_CHECKING": sshHostKeyCheckingModeGo(env),
		"HAAC_PROXMOX_ACCESS_HOST":   proxmoxAccessHostGo(env),
	}
	for _, key := range []string{
		"PROXMOX_HOST_PASSWORD",
		"LXC_PASSWORD",
		"NAS_PATH",
		"NAS_SHARE_NAME",
		"SMB_USER",
		"SMB_PASSWORD",
		"STORAGE_UID",
		"STORAGE_GID",
		"HAAC_ENABLE_FALCO",
		"LXC_K3S_COMPAT_MODE",
		"LXC_ENABLE_GPU_PASSTHROUGH",
		"LXC_ENABLE_TUN",
		"LXC_ENABLE_EBPF_MOUNTS",
	} {
		if value := strings.TrimSpace(env[key]); value != "" {
			overrides[key] = value
		}
	}
	for key, value := range overrides {
		mapped = upsertEnv(mapped, key, value)
	}
	return mapped
}

func runAnsibleWSLGo(repoRoot, inventoryPath, playbookPath string, extraArgs []string, env map[string]string) error {
	if _, err := exec.LookPath("wsl"); err != nil {
		return fmt.Errorf("Ansible on Windows requires WSL. Install WSL and make ansible-playbook available inside it.")
	}
	repoWSL, err := toPosixWSLPathGo(env, repoRoot)
	if err != nil {
		return err
	}
	inventoryWSL, err := toPosixWSLPathGo(env, inventoryPath)
	if err != nil {
		return err
	}
	playbookWSL, err := toPosixWSLPathGo(env, playbookPath)
	if err != nil {
		return err
	}
	kubeconfigWSL, err := toPosixWSLPathGo(env, localKubeconfigPathGo())
	if err != nil {
		return err
	}
	privateKeyWSL, cleanupSSH, err := ensureWSLSSHKeypairGo(repoRoot, env)
	if err != nil {
		return err
	}
	knownHostsWSL, cleanupKnownHosts, err := ensureWSLKnownHostsGo(repoRoot, env)
	if err != nil {
		cleanupSSH()
		return err
	}
	defer func() {
		cleanupKnownHosts()
		cleanupSSH()
	}()

	envExports := map[string]string{
		"HAAC_KUBECONFIG_PATH":       kubeconfigWSL,
		"HAAC_SSH_PRIVATE_KEY_PATH":  privateKeyWSL,
		"HAAC_SSH_KNOWN_HOSTS_PATH":  knownHostsWSL,
		"HAAC_SSH_HOST_KEY_CHECKING": sshHostKeyCheckingModeGo(env),
		"HAAC_PROXMOX_ACCESS_HOST":   proxmoxAccessHostGo(env),
	}
	for _, key := range []string{
		"PROXMOX_HOST_PASSWORD",
		"LXC_PASSWORD",
		"NAS_PATH",
		"NAS_SHARE_NAME",
		"SMB_USER",
		"SMB_PASSWORD",
		"STORAGE_UID",
		"STORAGE_GID",
		"HAAC_ENABLE_FALCO",
		"LXC_K3S_COMPAT_MODE",
		"LXC_ENABLE_GPU_PASSTHROUGH",
		"LXC_ENABLE_TUN",
		"LXC_ENABLE_EBPF_MOUNTS",
	} {
		if value := strings.TrimSpace(env[key]); value != "" {
			envExports[key] = value
		}
	}
	scriptLines := make([]string, 0, len(envExports)+3)
	for key, value := range envExports {
		scriptLines = append(scriptLines, fmt.Sprintf("export %s=%s", key, shellEscape(value)))
	}
	scriptLines = append(scriptLines,
		fmt.Sprintf("cd %s", shellEscape(repoWSL)),
		fmt.Sprintf("mkdir -p %s", shellEscape(pathpkg.Dir(kubeconfigWSL))),
		fmt.Sprintf("ansible-playbook %s -i %s %s", shellJoin(extraArgs), shellEscape(inventoryWSL), shellEscape(playbookWSL)),
	)
	command := exec.Command(
		"wsl",
		"-d",
		wslDistro(env),
		"--",
		"bash",
		"-se",
	)
	command.Dir = repoRoot
	command.Env = os.Environ()
	command.Stdout = os.Stdout
	command.Stderr = os.Stderr
	command.Stdin = strings.NewReader(strings.Join(scriptLines, "\n") + "\n")
	if err := command.Run(); err != nil {
		var exitErr *exec.ExitError
		if errors.As(err, &exitErr) {
			return fmt.Errorf("command failed with exit code %d", exitErr.ExitCode())
		}
		return err
	}
	return nil
}

func tofuCLIEnvGo(repoRoot string, env map[string]string) []string {
	mapped := os.Environ()
	for key, value := range tofuTFVarsGo(env) {
		mapped = upsertEnv(mapped, key, value)
	}
	return mapped
}

func tofuTFVarsGo(env map[string]string) map[string]string {
	direct := map[string]string{
		"lxc_password":               env["LXC_PASSWORD"],
		"lxc_rootfs_datastore":       env["LXC_ROOTFS_DATASTORE"],
		"lxc_master_hostname":        env["LXC_MASTER_HOSTNAME"],
		"lxc_master_memory":          env["LXC_MASTER_MEMORY"],
		"lxc_unprivileged":           env["LXC_UNPRIVILEGED"],
		"lxc_nesting":                env["LXC_NESTING"],
		"master_target_node":         env["MASTER_TARGET_NODE"],
		"k3s_master_ip":              env["K3S_MASTER_IP"],
		"worker_nodes":               env["WORKER_NODES_JSON"],
		"host_nas_path":              env["HOST_NAS_PATH"],
		"cloudflare_tunnel_token":    env["CLOUDFLARE_TUNNEL_TOKEN"],
		"domain_name":                env["DOMAIN_NAME"],
		"protonvpn_openvpn_username": env["PROTONVPN_OPENVPN_USERNAME"],
		"protonvpn_openvpn_password": env["PROTONVPN_OPENVPN_PASSWORD"],
		"smb_user":                   env["SMB_USER"],
		"smb_password":               env["SMB_PASSWORD"],
		"nas_address":                env["NAS_ADDRESS"],
		"nas_share_name":             env["NAS_SHARE_NAME"],
		"storage_uid":                env["STORAGE_UID"],
		"storage_gid":                env["STORAGE_GID"],
	}
	mapped := make(map[string]string, len(direct)+4)
	for key, value := range direct {
		mapped["TF_VAR_"+key] = value
	}
	mapped["TF_VAR_proxmox_access_host"] = proxmoxAccessHostGo(env)
	mapped["TF_VAR_lxc_gateway"] = resolveDefaultGatewayGo(env)
	mapped["TF_VAR_python_executable"] = firstNonEmpty(env["PYTHON_CMD"], "python")
	mapped["TF_VAR_maintenance_ssh_user"] = firstNonEmpty(env["MAINTENANCE_SSH_USER"], "root")
	return mapped
}

func migrateLegacyProxmoxDownloadFileStateGo(repoRoot, tofuDir, tofuBinary string, env map[string]string) error {
	addresses := make(map[string]struct{})
	listCmd := exec.Command(tofuBinary, "-chdir="+tofuDir, "state", "list")
	listCmd.Dir = repoRoot
	listCmd.Env = tofuCLIEnvGo(repoRoot, env)
	output, err := listCmd.Output()
	if err == nil {
		for _, line := range strings.Split(string(output), "\n") {
			line = strings.TrimSpace(line)
			if line != "" {
				addresses[line] = struct{}{}
			}
		}
	}
	if _, ok := addresses["proxmox_virtual_environment_download_file.debian_container_template"]; !ok {
		return nil
	}
	if _, ok := addresses["proxmox_download_file.debian_container_template"]; !ok {
		showCmd := exec.Command(tofuBinary, "-chdir="+tofuDir, "state", "show", "proxmox_virtual_environment_download_file.debian_container_template")
		showCmd.Dir = repoRoot
		showCmd.Env = tofuCLIEnvGo(repoRoot, env)
		showOutput, err := showCmd.Output()
		if err != nil {
			return fmt.Errorf("unable to inspect legacy OpenTofu state for proxmox_virtual_environment_download_file.debian_container_template")
		}
		match := regexp.MustCompile(`(?m)^\s*id\s*=\s*"?([^"\r\n]+)"?\s*$`).FindStringSubmatch(string(showOutput))
		if len(match) != 2 {
			return fmt.Errorf("unable to extract resource id from legacy OpenTofu state for proxmox_virtual_environment_download_file.debian_container_template")
		}
		fmt.Println("Migrating legacy Proxmox download-file state to proxmox_download_file.debian_container_template before plan/apply...")
		importCmd := exec.Command(tofuBinary, "-chdir="+tofuDir, "import", "proxmox_download_file.debian_container_template", strings.TrimSpace(match[1]))
		importCmd.Dir = repoRoot
		importCmd.Env = tofuCLIEnvGo(repoRoot, env)
		importCmd.Stdout = os.Stdout
		importCmd.Stderr = os.Stderr
		importCmd.Stdin = os.Stdin
		if err := importCmd.Run(); err != nil {
			return err
		}
	}
	fmt.Println("Removing legacy OpenTofu state entry proxmox_virtual_environment_download_file.debian_container_template...")
	rmCmd := exec.Command(tofuBinary, "-chdir="+tofuDir, "state", "rm", "proxmox_virtual_environment_download_file.debian_container_template")
	rmCmd.Dir = repoRoot
	rmCmd.Env = tofuCLIEnvGo(repoRoot, env)
	rmCmd.Stdout = os.Stdout
	rmCmd.Stderr = os.Stderr
	rmCmd.Stdin = os.Stdin
	return rmCmd.Run()
}

func tofuOutputRawGo(repoRoot, tofuBinary, tofuDir, name string) (string, error) {
	cmd := exec.Command(tofuBinary, "-chdir="+tofuDir, "output", "-raw", name)
	cmd.Dir = repoRoot
	output, err := cmd.Output()
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(output)), nil
}

func tofuOutputJSONValueGo(repoRoot, tofuBinary, tofuDir, name string) (any, error) {
	cmd := exec.Command(tofuBinary, "-chdir="+tofuDir, "output", "-json", name)
	cmd.Dir = repoRoot
	output, err := cmd.Output()
	if err != nil {
		return nil, err
	}
	var payload any
	if err := json.Unmarshal(output, &payload); err != nil {
		return nil, err
	}
	return payload, nil
}

func shellEscape(value string) string {
	if value == "" {
		return "''"
	}
	return "'" + strings.ReplaceAll(value, "'", `'"'"'`) + "'"
}

func shellJoin(values []string) string {
	parts := make([]string, 0, len(values))
	for _, value := range values {
		if strings.TrimSpace(value) == "" {
			continue
		}
		parts = append(parts, shellEscape(value))
	}
	return strings.Join(parts, " ")
}

func parseIntegerGo(value any) string {
	switch typed := value.(type) {
	case float64:
		return strconv.Itoa(int(typed))
	case int:
		return strconv.Itoa(typed)
	case int64:
		return strconv.FormatInt(typed, 10)
	case json.Number:
		return typed.String()
	default:
		rendered := strings.TrimSpace(fmt.Sprint(value))
		if rendered == "<nil>" {
			return ""
		}
		return rendered
	}
}

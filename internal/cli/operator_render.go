package cli

import (
	"bufio"
	"crypto/pbkdf2"
	"crypto/sha256"
	"crypto/sha512"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"github.com/GehirnInc/crypt/sha512_crypt"
)

const traefikDefaultTrustedIPsGo = "10.42.0.0/16,10.43.0.0/16,103.21.244.0/22,103.22.200.0/22,103.31.4.0/22,104.16.0.0/13,104.24.0.0/14,108.162.192.0/18,131.0.72.0/22,141.101.64.0/18,162.158.0.0/15,172.64.0.0/13,173.245.48.0/20,188.114.96.0/20,190.93.240.0/20,197.234.240.0/22,198.41.128.0/17,2400:cb00::/32,2606:4700::/32,2803:f800::/32,2405:b500::/32,2405:8100::/32,2a06:98c0::/29,2c0f:f248::/32"

var envPlaceholderPatternGo = regexp.MustCompile(`\$\{([A-Z0-9_]+)\}`)

func applyDerivedEnvDefaultsGo(repoRoot string, env map[string]string) error {
	setDefaultGo(env, "HAAC_FALCO_INGEST_NODEPORT", "32081")
	setDefaultGo(env, "TRAEFIK_TRUSTED_IPS", traefikDefaultTrustedIPsGo)
	setDefaultGo(env, "CROWDSEC_WEBUI_IMAGE_REPOSITORY", "ghcr.io/theduffman85/crowdsec-web-ui")
	setDefaultGo(env, "CROWDSEC_WEBUI_IMAGE_TAG", "2026.4.12")
	if value := envValueGo(env, "GRAFANA_OIDC_SECRET"); value != "" {
		setDefaultGo(env, "GRAFANA_OIDC_SECRET_SHA256", sha256HexGo(value))
	}
	if password := envValueGo(env, "QUI_PASSWORD"); password != "" {
		setDefaultGo(env, "QBITTORRENT_PASSWORD_PBKDF2", qbittorrentPasswordPBKDF2Go(password))
		setDefaultGo(env, "DOWNLOADERS_AUTH_SECRET_SHA256", stableSecretChecksumGo(map[string]string{
			"QBITTORRENT_USERNAME":        firstNonEmpty(env["QBITTORRENT_USERNAME"], "admin"),
			"QUI_PASSWORD":                password,
			"QBITTORRENT_PASSWORD_PBKDF2": env["QBITTORRENT_PASSWORD_PBKDF2"],
		}))
	}
	if envValueGo(env, "PROTONVPN_OPENVPN_USERNAME") != "" && envValueGo(env, "PROTONVPN_OPENVPN_PASSWORD") != "" {
		setDefaultGo(env, "PROTONVPN_SECRET_SHA256", stableSecretChecksumGo(map[string]string{
			"OPENVPN_USER":     protonvpnPortForwardUsernameGo(env["PROTONVPN_OPENVPN_USERNAME"]),
			"OPENVPN_PASSWORD": env["PROTONVPN_OPENVPN_PASSWORD"],
		}))
	}
	if envValueGo(env, "QUI_PASSWORD") != "" && envValueGo(env, "GRAFANA_ADMIN_PASSWORD") != "" {
		setDefaultGo(env, "HOMEPAGE_WIDGETS_SECRET_SHA256", stableSecretChecksumGo(map[string]string{
			"HOMEPAGE_VAR_GRAFANA_USERNAME":     firstNonEmpty(env["GRAFANA_ADMIN_USERNAME"], "admin"),
			"HOMEPAGE_VAR_GRAFANA_PASSWORD":     env["GRAFANA_ADMIN_PASSWORD"],
			"HOMEPAGE_VAR_QBITTORRENT_USERNAME": firstNonEmpty(env["QBITTORRENT_USERNAME"], "admin"),
			"HOMEPAGE_VAR_QBITTORRENT_PASSWORD": env["QUI_PASSWORD"],
		}))
	}
	if envValueGo(env, "CROWDSEC_BOUNCER_KEY") != "" {
		dynamic := crowdsecTraefikDynamicConfigGo(env)
		setDefaultGo(env, "CROWDSEC_TRAEFIK_SECRET_SHA256", stableSecretChecksumGo(map[string]string{
			"crowdsec-bouncer.yaml": dynamic,
			"crowdsec-lapi-key":     env["CROWDSEC_BOUNCER_KEY"],
		}))
		crowdsecWebUIUsername, crowdsecWebUIPassword, err := crowdsecWebUICredentialsGo(env)
		if err != nil {
			return err
		}
		setDefaultGo(env, "CROWDSEC_WEBUI_SECRET_SHA256", stableSecretChecksumGo(map[string]string{
			"CROWDSEC_USER":     crowdsecWebUIUsername,
			"CROWDSEC_PASSWORD": crowdsecWebUIPassword,
		}))
	}
	if _, ok := env["HOMEPAGE_CONFIG_CHECKSUM"]; !ok {
		checksum, err := homepageConfigChecksumGo(repoRoot, env)
		if err != nil {
			return err
		}
		env["HOMEPAGE_CONFIG_CHECKSUM"] = checksum
	}
	return nil
}

func sha256HexGo(value string) string {
	sum := sha256.Sum256([]byte(value))
	return hex.EncodeToString(sum[:])
}

func stableSecretChecksumGo(values map[string]string) string {
	keys := make([]string, 0, len(values))
	for key := range values {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	lines := make([]string, 0, len(keys))
	for _, key := range keys {
		lines = append(lines, key+"="+values[key])
	}
	return sha256HexGo(strings.Join(lines, "\n"))
}

func protonvpnPortForwardUsernameGo(username string) string {
	raw := strings.TrimSpace(username)
	if raw == "" {
		return ""
	}
	parts := strings.Split(raw, "+")
	base := parts[0]
	suffixes := []string{}
	for _, part := range parts[1:] {
		cleaned := strings.TrimSpace(part)
		if cleaned == "" {
			continue
		}
		switch strings.ToLower(cleaned) {
		case "pmp", "nr":
			continue
		default:
			suffixes = append(suffixes, cleaned)
		}
	}
	suffixes = append(suffixes, "pmp")
	return strings.Join(append([]string{base}, suffixes...), "+")
}

func qbittorrentPasswordPBKDF2Go(password string) string {
	saltSum := sha256.Sum256([]byte("haac-qbittorrent:" + password))
	salt := saltSum[:16]
	derived, err := pbkdf2.Key(sha512.New, password, salt, 100000, 64)
	if err != nil {
		return ""
	}
	return fmt.Sprintf("@ByteArray(%s:%s)", base64.StdEncoding.EncodeToString(salt), base64.StdEncoding.EncodeToString(derived))
}

func trustedIPListGo(raw string) []string {
	seen := map[string]struct{}{}
	values := []string{}
	for _, item := range strings.Split(raw, ",") {
		candidate := strings.TrimSpace(item)
		if candidate == "" {
			continue
		}
		if _, ok := seen[candidate]; ok {
			continue
		}
		seen[candidate] = struct{}{}
		values = append(values, candidate)
	}
	return values
}

func crowdsecTraefikDynamicConfigGo(env map[string]string) string {
	trusted := trustedIPListGo(env["TRAEFIK_TRUSTED_IPS"])
	if len(trusted) == 0 {
		trusted = trustedIPListGo(traefikDefaultTrustedIPsGo)
	}
	lines := make([]string, 0, len(trusted))
	for _, cidr := range trusted {
		lines = append(lines, "            - "+cidr)
	}
	return "http:\n" +
		"  middlewares:\n" +
		"    crowdsec-bouncer:\n" +
		"      plugin:\n" +
		"        crowdsec-bouncer-traefik-plugin:\n" +
		"          enabled: true\n" +
		"          logLevel: INFO\n" +
		"          metricsUpdateIntervalSeconds: 60\n" +
		"          crowdsecMode: stream\n" +
		"          crowdsecLapiScheme: http\n" +
		"          crowdsecLapiHost: crowdsec-service.crowdsec.svc.cluster.local:8080\n" +
		"          crowdsecLapiKeyFile: /etc/traefik/crowdsec/auth/crowdsec-lapi-key\n" +
		"          crowdsecAppsecEnabled: true\n" +
		"          crowdsecAppsecHost: crowdsec-appsec-service.crowdsec.svc.cluster.local:7422\n" +
		"          crowdsecAppsecFailureBlock: true\n" +
		"          crowdsecAppsecUnreachableBlock: false\n" +
		"          forwardedHeadersTrustedIPs:\n" +
		strings.Join(lines, "\n") + "\n"
}

func renderEnvPlaceholdersGo(content string, env map[string]string) string {
	return envPlaceholderPatternGo.ReplaceAllStringFunc(content, func(token string) string {
		matches := envPlaceholderPatternGo.FindStringSubmatch(token)
		if len(matches) != 2 {
			return token
		}
		if value, ok := env[matches[1]]; ok {
			return value
		}
		return token
	})
}

func renderValuesFileGo(repoRoot string, env map[string]string) error {
	templatePath := repoJoin(repoRoot, valuesTemplateRel)
	outputPath := repoJoin(repoRoot, valuesOutputRel)
	content, err := readFileWithRetryGo(templatePath)
	if err != nil {
		return err
	}
	return writeFileWithRetryGo(outputPath, []byte(renderEnvPlaceholdersGo(string(content), env)), 0o644)
}

func gitopsTemplatePathGo(outputPath string) string {
	return filepath.Join(filepath.Dir(outputPath), filepath.Base(outputPath)+".template")
}

func renderGitopsManifestsGo(repoRoot string, env map[string]string) error {
	if err := validateFalcoRuntimeInputsGo(env); err != nil {
		return err
	}
	for _, rel := range gitopsRenderedOutputRels {
		outputPath := repoJoin(repoRoot, rel)
		templatePath := gitopsTemplatePathGo(outputPath)
		if !fileExists(templatePath) {
			return fmt.Errorf("missing GitOps manifest template: %s", templatePath)
		}
		if (rel == falcoAppRel || rel == falcoIngestServiceRel) && !falcoEnabledGo(env) {
			if err := writeFileWithRetryGo(outputPath, []byte("apiVersion: v1\nkind: List\nitems: []\n"), 0o644); err != nil {
				return err
			}
			continue
		}
		content, err := readFileWithRetryGo(templatePath)
		if err != nil {
			return err
		}
		if err := writeFileWithRetryGo(outputPath, []byte(renderEnvPlaceholdersGo(string(content), env)), 0o644); err != nil {
			return err
		}
	}
	return nil
}

func falcoEnabledGo(env map[string]string) bool {
	if value, ok := env["HAAC_ENABLE_FALCO"]; ok {
		return truthyGo(value)
	}
	return !truthyGo(firstNonEmpty(env["LXC_UNPRIVILEGED"], "true"))
}

func validateFalcoRuntimeInputsGo(env map[string]string) error {
	if !falcoEnabledGo(env) {
		return nil
	}
	raw := firstNonEmpty(env["HAAC_FALCO_INGEST_NODEPORT"], "32081")
	nodePort, err := strconv.Atoi(raw)
	if err != nil {
		return fmt.Errorf("HAAC_FALCO_INGEST_NODEPORT must be a valid integer node port")
	}
	if nodePort < 30000 || nodePort > 32767 {
		return fmt.Errorf("HAAC_FALCO_INGEST_NODEPORT must be within the Kubernetes NodePort range 30000-32767")
	}
	return nil
}

func truthyGo(value string) bool {
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "1", "true", "yes", "on":
		return true
	default:
		return false
	}
}

func homepageConfigChecksumGo(repoRoot string, env map[string]string) (string, error) {
	content, err := readFileWithRetryGo(repoJoin(repoRoot, valuesTemplateRel))
	if err != nil {
		return "", err
	}
	rendered := renderEnvPlaceholdersGo(string(content), env)
	input := extractTopLevelYAMLSectionGo(rendered, "ingresses") + "\n---\n" + extractTopLevelYAMLSectionGo(rendered, "homepage")
	return sha256HexGo(input), nil
}

func extractTopLevelYAMLSectionGo(content, sectionName string) string {
	header := sectionName + ":"
	topLevel := regexp.MustCompile(`^[A-Za-z0-9_-]+:\s*(?:#.*)?$`)
	capturing := false
	lines := []string{}
	scanner := bufio.NewScanner(strings.NewReader(content))
	for scanner.Scan() {
		line := scanner.Text()
		if !capturing {
			if strings.HasPrefix(line, header) {
				capturing = true
				lines = append(lines, line)
			}
			continue
		}
		if line != "" && !strings.HasPrefix(line, " ") && !strings.HasPrefix(line, "\t") && topLevel.MatchString(line) {
			break
		}
		lines = append(lines, line)
	}
	return strings.TrimSpace(strings.Join(lines, "\n"))
}

func renderAutheliaGo(repoRoot, outputDir string, env map[string]string) (string, string, error) {
	hash, err := resolveAutheliaAdminPasswordHashGo(repoRoot, env)
	if err != nil {
		return "", "", err
	}
	env["AUTHELIA_ADMIN_PASSWORD_HASH"] = hash
	keyContent := readAutheliaOIDCKeyGo(outputDir, env)
	configOutput := filepath.Join(outputDir, "authelia_configuration.yml")
	usersOutput := filepath.Join(outputDir, "authelia_users.yml")
	if err := hydrateAutheliaTemplateGo(repoJoin(repoRoot, autheliaConfigTmplRel), configOutput, env, keyContent); err != nil {
		return "", "", err
	}
	if err := hydrateAutheliaTemplateGo(repoJoin(repoRoot, autheliaUsersTmplRel), usersOutput, env, keyContent); err != nil {
		return "", "", err
	}
	return configOutput, usersOutput, nil
}

func resolveAutheliaAdminPasswordHashGo(repoRoot string, env map[string]string) (string, error) {
	password := envValueGo(env, "AUTHELIA_ADMIN_PASSWORD")
	existing := envValueGo(env, "AUTHELIA_ADMIN_PASSWORD_HASH")
	if password == "" {
		return existing, nil
	}
	crypter := sha512_crypt.New()
	if existing != "" && crypter.Verify(existing, []byte(password)) == nil {
		return existing, nil
	}
	hash, err := crypter.Generate([]byte(password), nil)
	if err != nil {
		return "", err
	}
	if err := persistEnvValueGo(filepath.Join(repoRoot, ".env"), "AUTHELIA_ADMIN_PASSWORD_HASH", hash); err != nil {
		return "", err
	}
	return hash, nil
}

func persistEnvValueGo(envFile, key, value string) error {
	if !fileExists(envFile) {
		return nil
	}
	data, err := readFileWithRetryGo(envFile)
	if err != nil {
		return err
	}
	lines := strings.Split(strings.ReplaceAll(string(data), "\r\n", "\n"), "\n")
	rendered := key + "=" + quoteStringYAMLGo(value)
	updated := false
	for i, line := range lines {
		if strings.HasPrefix(line, key+"=") {
			lines[i] = rendered
			updated = true
			break
		}
	}
	if !updated {
		if len(lines) > 0 && strings.TrimSpace(lines[len(lines)-1]) == "" {
			lines[len(lines)-1] = rendered
		} else {
			lines = append(lines, rendered)
		}
	}
	return writeFileWithRetryGo(envFile, []byte(strings.Join(lines, "\n")+"\n"), 0o600)
}

func readAutheliaOIDCKeyGo(outputDir string, env map[string]string) string {
	if encoded := envValueGo(env, "AUTHELIA_OIDC_PRIVATE_KEY_B64"); encoded != "" {
		if decoded, err := base64.StdEncoding.DecodeString(encoded); err == nil {
			return strings.TrimSpace(string(decoded))
		}
	}
	for _, candidate := range []string{
		filepath.Join(outputDir, "oidc_key.pem"),
		filepath.Join(os.TempDir(), "oidc_key.pem"),
		filepath.FromSlash("/tmp/oidc_key.pem"),
	} {
		if data, err := readFileWithRetryGo(candidate); err == nil {
			return strings.TrimSpace(string(data))
		}
	}
	return ""
}

func hydrateAutheliaTemplateGo(templatePath, outputPath string, env map[string]string, keyContent string) error {
	data, err := readFileWithRetryGo(templatePath)
	if err != nil {
		return err
	}
	lines := strings.SplitAfter(string(data), "\n")
	var builder strings.Builder
	for _, line := range lines {
		if strings.Contains(line, "${INDENTED_OIDC_KEY}") {
			indent := strings.Repeat(" ", strings.Index(line, "${INDENTED_OIDC_KEY}"))
			keyLines := strings.Split(strings.TrimRight(keyContent, "\n"), "\n")
			if len(keyLines) == 0 {
				keyLines = []string{""}
			}
			for _, keyLine := range keyLines {
				builder.WriteString(indent)
				builder.WriteString(keyLine)
				builder.WriteByte('\n')
			}
			continue
		}
		builder.WriteString(renderEnvPlaceholdersGo(line, env))
	}
	if err := os.MkdirAll(filepath.Dir(outputPath), 0o755); err != nil {
		return err
	}
	return writeFileWithRetryGo(outputPath, []byte(builder.String()), 0o600)
}

func quoteStringYAMLGo(value string) string {
	encoded, _ := json.Marshal(value)
	return string(encoded)
}

func bazarrAuthIdentityGo(env map[string]string) (string, string, error) {
	username := envValueGo(env, "BAZARR_AUTH_USERNAME")
	password := envValueGo(env, "BAZARR_AUTH_PASSWORD")
	if username == "" || password == "" {
		return "", "", fmt.Errorf("Bazarr bootstrap needs native auth credentials. Set BAZARR_AUTH_USERNAME/BAZARR_AUTH_PASSWORD or let them derive from HAAC_MAIN_*")
	}
	return username, password, nil
}

func repoURLRequiresSSHAuthGo(repoURL string) bool {
	lowered := strings.ToLower(strings.TrimSpace(repoURL))
	return strings.HasPrefix(lowered, "git@") || strings.HasPrefix(lowered, "ssh://")
}

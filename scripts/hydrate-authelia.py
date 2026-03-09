import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(CURRENT_DIR, "../k8s/charts/haac-stack/config-templates")

# Load .env
env_path = os.path.join(CURRENT_DIR, "../.env")
env = {}
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                env[k] = v.strip('"').strip("'")

# Special case for RSA Key
key_content = ""
# 1. Try to get it from .env (Base64 encoded)
if env.get("AUTHELIA_OIDC_PRIVATE_KEY_B64"):
    import base64

    try:
        key_content = (
            base64.b64decode(env["AUTHELIA_OIDC_PRIVATE_KEY_B64"])
            .decode("utf-8")
            .strip()
        )
    except Exception as e:
        print(f"Error decoding AUTHELIA_OIDC_PRIVATE_KEY_B64: {e}")

# 2. Fallback to /tmp/oidc_key.pem if not in .env or decoding failed
if not key_content and os.path.exists("/tmp/oidc_key.pem"):
    with open("/tmp/oidc_key.pem") as f:
        key_content = f.read().strip()

# Get DOMAIN_NAME from environment with a default
domain_name = os.environ.get("DOMAIN_NAME")


def hydrate(template_path, output_path):
    with open(template_path) as f:
        lines = f.readlines()

    output_lines = []
    for line in lines:
        if "${INDENTED_OIDC_KEY}" in line:
            # Get the exact indentation of the placeholder
            indent_size = line.find("${INDENTED_OIDC_KEY}")
            indent = " " * indent_size
            # Indent every line of the key content
            for key_line in key_content.split("\n"):
                output_lines.append(indent + key_line + "\n")
        else:
            # Replace basic variables in the line
            new_line = line
            for k, v in env.items():
                placeholder = "${" + k + "}"
                new_line = new_line.replace(placeholder, v)
            output_lines.append(new_line)

    with open(output_path, "w") as f:
        f.writelines(output_lines)


if __name__ == "__main__":
    hydrate(
        os.path.join(TEMPLATE_DIR, "configuration.yml.template"),
        "/tmp/authelia_configuration.yml",
    )
    hydrate(
        os.path.join(TEMPLATE_DIR, "users.yml.template"),
        "/tmp/authelia_users.yml",
    )

{{- define "haac-stack.homepage.settings" -}}
title: "Nucleo Autogenerativo"
theme: dark
proxy: true
layout:
{{- $ingresses := .Values.ingresses | default dict -}}
{{- $groups := dict -}}
{{- range $name := keys $ingresses | sortAlpha }}
{{- $conf := index $ingresses $name }}
{{- if (default true $conf.enabled) }}
{{- $group := default "Management" $conf.homepage_group }}
{{- $existing := get $groups $group | default (list) }}
{{- $_ := set $groups $group (append $existing (dict "name" $name "conf" $conf)) }}
{{- end }}
{{- end }}
{{- range $group := keys $groups | sortAlpha }}
  {{ $group }}:
    style: row
    columns: 3
{{- end }}
{{- end }}

{{- define "haac-stack.homepage.services" -}}
{{- $ingresses := .Values.ingresses | default dict -}}
{{- $groups := dict -}}
{{- range $name := keys $ingresses | sortAlpha }}
{{- $conf := index $ingresses $name }}
{{- if (default true $conf.enabled) }}
{{- $group := default "Management" $conf.homepage_group }}
{{- $existing := get $groups $group | default (list) }}
{{- $_ := set $groups $group (append $existing (dict "name" $name "conf" $conf)) }}
{{- end }}
{{- end }}
{{- range $group := keys $groups | sortAlpha }}
- {{ $group }}:
{{- range $entry := get $groups $group }}
{{- $name := $entry.name }}
{{- $conf := $entry.conf }}
    - {{ default $name $conf.homepage_name | quote }}:
        icon: {{ default "globe.png" $conf.homepage_icon | quote }}
        href: {{ printf "https://%s.%s" $conf.subdomain $.Values.global.domainName | quote }}
        description: {{ default "" $conf.homepage_description | quote }}
{{- end }}
{{- end }}
{{- end }}

{{- define "haac-stack.homepage.widgets" -}}
- greeting:
    text: "Benvenuto nel Nucleo Autogenerativo"
- datetime:
    format:
      date: long
      time: short
{{- end }}

{{- define "haac-stack.homepage.bookmarks" -}}
- Infrastructure:
    - Proxmox:
        - href: "https://192.168.0.211:8006"
          icon: proxmox.png
    - GitHub:
        - href: "https://github.com"
          icon: github.png
{{- end }}

{{- define "haac-stack.homepage.configChecksum" -}}
{{- printf "%s\n---\n%s\n---\n%s\n---\n%s" (include "haac-stack.homepage.settings" .) (include "haac-stack.homepage.services" .) (include "haac-stack.homepage.widgets" .) (include "haac-stack.homepage.bookmarks" .) | sha256sum -}}
{{- end }}

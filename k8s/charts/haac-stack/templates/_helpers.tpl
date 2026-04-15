{{- define "haac-stack.homepage.groupedEntries" -}}
{{- $ingresses := .Values.ingresses | default dict -}}
{{- $groups := dict -}}
{{- range $name := keys $ingresses | sortAlpha }}
{{- $conf := index $ingresses $name }}
{{- if (default true $conf.enabled) }}
{{- $group := default "Management" $conf.homepage_group }}
{{- $entry := dict
      "name" (default $name $conf.homepage_name)
      "icon" (default "globe.png" $conf.homepage_icon)
      "href" (printf "https://%s.%s" $conf.subdomain $.Values.global.domainName)
      "description" (default "" $conf.homepage_description)
}}
{{- $existing := get $groups $group | default (list) }}
{{- $_ := set $groups $group (append $existing $entry) }}
{{- end }}
{{- end }}
{{- $homepage := index .Values "homepage" | default dict }}
{{- $extraGroups := index $homepage "extraLinks" | default dict }}
{{- range $group := keys $extraGroups | sortAlpha }}
{{- $existing := get $groups $group | default (list) }}
{{- range $entry := get $extraGroups $group }}
{{- $merged := dict
      "name" (default "External" $entry.name)
      "icon" (default "globe.png" $entry.icon)
      "href" (default "#" $entry.href)
      "description" (default "" $entry.description)
}}
{{- $existing = append $existing $merged }}
{{- end }}
{{- $_ := set $groups $group $existing }}
{{- end }}
{{- toYaml $groups -}}
{{- end }}

{{- define "haac-stack.homepage.settings" -}}
title: "Nucleo Autogenerativo"
theme: dark
proxy: true
layout:
{{- $groups := include "haac-stack.homepage.groupedEntries" . | fromYaml | default dict }}
{{- range $group := keys $groups | sortAlpha }}
  {{ $group }}:
    style: row
    columns: 3
{{- end }}
{{- end }}

{{- define "haac-stack.homepage.services" -}}
{{- $groups := include "haac-stack.homepage.groupedEntries" . | fromYaml | default dict }}
{{- range $group := keys $groups | sortAlpha }}
- {{ $group }}:
{{- range $entry := get $groups $group }}
    - {{ $entry.name | quote }}:
        icon: {{ $entry.icon | quote }}
        href: {{ $entry.href | quote }}
        description: {{ $entry.description | quote }}
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
{{- $homepage := index .Values "homepage" | default dict }}
{{- $bookmarks := index $homepage "bookmarks" | default dict }}
{{- range $group := keys $bookmarks | sortAlpha }}
- {{ $group }}:
{{- range $entry := get $bookmarks $group }}
    - {{ default "External" $entry.name }}:
        - href: {{ default "#" $entry.href | quote }}
          icon: {{ default "globe.png" $entry.icon | quote }}
{{- end }}
{{- end }}
{{- end }}

{{- define "haac-stack.homepage.configChecksum" -}}
{{- printf "%s\n---\n%s\n---\n%s\n---\n%s" (include "haac-stack.homepage.settings" .) (include "haac-stack.homepage.services" .) (include "haac-stack.homepage.widgets" .) (include "haac-stack.homepage.bookmarks" .) | sha256sum -}}
{{- end }}

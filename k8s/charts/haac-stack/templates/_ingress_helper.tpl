{{- define "haac-stack.ingress.url" -}}
{{- printf "%s.%s" .subdomain $.Values.global.domainName -}}
{{- end -}}

{{- define "name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{- define "labels" -}}
app: {{ include "name" . }}
app.kubernetes.io/name: {{ include "name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- /* The metrics configuration, as JSON. Either form may be used. */ -}}
{{- define "metricsConfig" -}}
{{- if .Values.metricsConfigJson -}}
{{- .Values.metricsConfigJson -}}
{{- else if .Values.metricsConfig -}}
{{- .Values.metricsConfig | toJson -}}
{{- else -}}
{{- fail "Set metricsConfig (YAML object) or metricsConfigJson (JSON string). See README.md." -}}
{{- end -}}
{{- end }}

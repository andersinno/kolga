{{/* vim: set filetype=mustache: */}}

{{/*
Create a default fully qualified app name.
We truncate the name at 52 chars because some Kubernetes name fields are limited to this
(by the DNS naming spec) and we may postfix the name with "-initialize" (extra 11 chars).
*/}}

{{- define "trackableappname" -}}
{{- $trackableName := printf "%s-%s" (include "appname" .) .Values.application.track -}}
{{- $trackableName | trimSuffix "-stable" | trunc 52 | trimSuffix "-" -}}
{{- end -}}

{{- define "appname" -}}
{{- $releaseName := default .Release.Name .Values.releaseOverride -}}
{{- printf "%s" $releaseName | trunc 52 | trimSuffix "-" -}}
{{- end -}}

{{/*
Get a hostname from URL
*/}}
{{- define "hostname" -}}
{{- . | trimPrefix "http://" |  trimPrefix "https://" | trimSuffix "/" | quote -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "commonLabels" -}}
{{ include "selectorLabels" . }}
{{- end -}}

{{/*
Selector labels
*/}}
{{- define "selectorLabels" -}}
app: {{ include "appname" . | quote }}
release: {{ .Release.Name | quote }}
track: {{ .Values.application.track | quote }}
{{- end -}}

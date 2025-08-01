{{/*
Expand the name of the chart.
*/}}
{{- define "nautilus-trader.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "nautilus-trader.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "nautilus-trader.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "nautilus-trader.labels" -}}
helm.sh/chart: {{ include "nautilus-trader.chart" . }}
{{ include "nautilus-trader.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "nautilus-trader.selectorLabels" -}}
app.kubernetes.io/name: {{ include "nautilus-trader.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "nautilus-trader.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "nautilus-trader.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the config map
*/}}
{{- define "nautilus-trader.configMapName" -}}
{{- printf "%s-config" (include "nautilus-trader.fullname" .) }}
{{- end }}

{{/*
Create the name of the secret
*/}}
{{- define "nautilus-trader.secretName" -}}
{{- printf "%s-secrets" (include "nautilus-trader.fullname" .) }}
{{- end }}

{{/*
Database connection string
*/}}
{{- define "nautilus-trader.databaseUrl" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "postgresql://%s:%s@%s-postgresql:5432/%s" .Values.postgresql.auth.username .Values.postgresql.auth.password .Release.Name .Values.postgresql.auth.database }}
{{- else }}
{{- .Values.externalDatabase.url }}
{{- end }}
{{- end }}

{{/*
Redis connection string
*/}}
{{- define "nautilus-trader.redisUrl" -}}
{{- if .Values.redis.enabled }}
{{- printf "redis://:%s@%s-redis-master:6379/0" .Values.redis.auth.password .Release.Name }}
{{- else }}
{{- .Values.externalRedis.url }}
{{- end }}
{{- end }}

{{/*
RabbitMQ connection string
*/}}
{{- define "nautilus-trader.rabbitmqUrl" -}}
{{- if .Values.rabbitmq.enabled }}
{{- printf "amqp://%s:%s@%s-rabbitmq:5672/" .Values.rabbitmq.auth.username .Values.rabbitmq.auth.password .Release.Name }}
{{- else }}
{{- .Values.externalRabbitmq.url }}
{{- end }}
{{- end }}
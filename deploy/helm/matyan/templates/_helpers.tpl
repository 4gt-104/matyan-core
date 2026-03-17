{{- define "matyan.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "matyan.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "matyan.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" -}}
{{- end -}}

{{- define "matyan.labels" -}}
helm.sh/chart: {{ include "matyan.chart" . }}
app.kubernetes.io/name: {{ include "matyan.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.commonLabels }}
{{ toYaml . }}
{{- end }}
{{- end -}}

{{- define "matyan.selectorLabels" -}}
app.kubernetes.io/name: {{ include "matyan.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "matyan.commonAnnotations" -}}
{{- with .Values.commonAnnotations }}
{{- toYaml . }}
{{- end }}
{{- end -}}


{{- define "matyan.fdbOperatorProvidesCluster" -}}
{{- if and (index .Values "fdb-operator").install (index .Values "fdb-cluster").install }}true{{ end -}}
{{- end -}}

{{- define "matyan.fdbHaveClusterFile" -}}
{{- $fdb := index .Values "fdb-cluster" -}}
{{- if or (include "matyan.fdbOperatorProvidesCluster" .) $fdb.existingConfigMap $fdb.existingSecret $fdb.clusterFileContent }}true{{ end -}}
{{- end -}}

{{- define "matyan.fdbConfigMapName" -}}
{{- $fdb := index .Values "fdb-cluster" -}}
{{- if include "matyan.fdbOperatorProvidesCluster" . -}}
{{- printf "%s-config" (default .Release.Name $fdb.clusterName) -}}
{{- else if $fdb.existingConfigMap -}}
{{- $fdb.existingConfigMap -}}
{{- else -}}
{{- printf "%s-fdb-cluster" (include "matyan.fullname" .) -}}
{{- end -}}
{{- end -}}

{{- define "matyan.fdbClusterFileKey" -}}
{{- $fdb := index .Values "fdb-cluster" -}}
{{- if include "matyan.fdbOperatorProvidesCluster" . -}}
{{- $fdb.operatorConfigMapKey -}}
{{- else -}}
{{- .Values.fdbClient.clusterFileKey -}}
{{- end -}}
{{- end -}}

{{- define "matyan.hostname" -}}
{{- . | trimPrefix "https://" | trimPrefix "http://" -}}
{{- end -}}

{{- define "matyan.corsOrigins" -}}
{{- $origins := .Values.cors.origins -}}
{{- $origins = append $origins .Values.ui.hostBase -}}
{{- $origins | toJson -}}
{{- end -}}

{{- define "matyan.uiApiHostBase" -}}
{{- if .Values.ui.apiHostBase -}}
{{- .Values.ui.apiHostBase -}}
{{- else -}}
{{- .Values.backend.hostBase -}}
{{- end -}}
{{- end -}}

{{- define "matyan.kafkaSecurityProtocol" -}}
{{- if .Values.kafka.install -}}
{{- $protocol := .Values.kafka.listeners.client.protocol -}}
{{- if and $protocol (ne $protocol "PLAINTEXT") -}}{{- $protocol -}}{{- end -}}
{{- else -}}
{{- .Values.kafkaClient.securityProtocol -}}
{{- end -}}
{{- end -}}

{{- define "matyan.kafkaSaslMechanism" -}}
{{- if .Values.kafka.install -}}
{{- with .Values.kafka.sasl.enabledMechanisms -}}
{{- . | splitList "," | first | trim -}}
{{- end -}}
{{- else -}}
{{- .Values.kafkaClient.saslMechanism -}}
{{- end -}}
{{- end -}}

{{- define "matyan.kafkaBootstrapServers" -}}
{{- if .Values.kafkaClient.bootstrapServers -}}
{{- .Values.kafkaClient.bootstrapServers -}}
{{- else if .Values.kafka.install -}}
{{- printf "%s-kafka:9092" .Release.Name -}}
{{- else -}}
{{- fail "kafkaClient.bootstrapServers is required when kafka.install is false" -}}
{{- end -}}
{{- end -}}

{{- define "matyan.s3Endpoint" -}}
{{- if .Values.rustfs.install -}}
{{- printf "http://%s-rustfs-svc:9000" .Release.Name -}}
{{- else -}}
{{- .Values.s3.endpoint -}}
{{- end -}}
{{- end -}}

{{- define "matyan.s3PublicEndpoint" -}}
{{- if .Values.s3.publicEndpoint -}}
{{- .Values.s3.publicEndpoint -}}
{{- else if and .Values.rustfs.install .Values.rustfs.s3Ingress.enabled (gt (len .Values.rustfs.s3Ingress.hosts) 0) -}}
{{- $scheme := "http" -}}
{{- if gt (len .Values.rustfs.s3Ingress.tls) 0 -}}{{- $scheme = "https" -}}{{- end -}}
{{- printf "%s://%s" $scheme (index .Values.rustfs.s3Ingress.hosts 0).host -}}
{{- else -}}
{{- include "matyan.s3Endpoint" . -}}
{{- end -}}
{{- end -}}

{{- define "matyan.s3AccessKey" -}}
{{- if .Values.rustfs.install -}}
{{- .Values.rustfs.auth.accessKey -}}
{{- else -}}
{{- .Values.s3.accessKey -}}
{{- end -}}
{{- end -}}

{{- define "matyan.s3SecretKey" -}}
{{- if .Values.rustfs.install -}}
{{- .Values.rustfs.auth.secretKey -}}
{{- else -}}
{{- .Values.s3.secretKey -}}
{{- end -}}
{{- end -}}

{{/*
Render a single FDB process-class entry (customParameters, podTemplate, volumeClaimTemplate).
Accepts a dict with optional keys: customParameters, podTemplate, volumeClaimTemplate.
*/}}
{{- define "matyan.fdbProcessEntry" -}}
{{- $p := . -}}
{{- $pt := $p.podTemplate | default dict -}}
{{- $fdbC := $pt.foundationdb | default dict -}}
{{- $sideC := $pt.sidecar | default dict -}}
{{- $initC := $pt.init | default dict -}}
{{- $vcl := $p.volumeClaimTemplate | default dict -}}
{{- $hasCustomParams := and (hasKey $p "customParameters") (gt (len $p.customParameters) 0) -}}
{{- $hasFdb := or (gt (len ($fdbC.resources | default dict)) 0) (gt (len ($fdbC.securityContext | default dict)) 0) -}}
{{- $hasSidecar := or (gt (len ($sideC.resources | default dict)) 0) (gt (len ($sideC.securityContext | default dict)) 0) -}}
{{- $hasInit := or (gt (len ($initC.resources | default dict)) 0) (gt (len ($initC.securityContext | default dict)) 0) -}}
{{- $hasContainers := or $hasFdb $hasSidecar $hasInit -}}
{{- $hasScheduling := or ($pt.nodeSelector) ($pt.affinity) ($pt.tolerations) ($pt.topologySpreadConstraints) -}}
{{- $hasPodTemplate := or $hasContainers $hasScheduling -}}
{{- $hasVCL := or ($vcl.storageClassName) ($vcl.storage) -}}
{{- if $hasCustomParams }}
customParameters:
  {{- toYaml $p.customParameters | nindent 2 }}
{{- end }}
{{- if $hasPodTemplate }}
podTemplate:
  spec:
    containers:
      - name: foundationdb
        {{- with $fdbC.resources }}
        resources:
          {{- toYaml . | nindent 10 }}
        {{- end }}
        {{- with $fdbC.securityContext }}
        securityContext:
          {{- toYaml . | nindent 10 }}
        {{- end }}
      - name: foundationdb-kubernetes-sidecar
        {{- with $sideC.resources }}
        resources:
          {{- toYaml . | nindent 10 }}
        {{- end }}
        {{- with $sideC.securityContext }}
        securityContext:
          {{- toYaml . | nindent 10 }}
        {{- end }}
    {{- if $hasInit }}
    initContainers:
      - name: foundationdb-kubernetes-init
        {{- with $initC.resources }}
        resources:
          {{- toYaml . | nindent 10 }}
        {{- end }}
        {{- with $initC.securityContext }}
        securityContext:
          {{- toYaml . | nindent 10 }}
        {{- end }}
    {{- end }}
    {{- with $pt.nodeSelector }}
    nodeSelector:
      {{- toYaml . | nindent 6 }}
    {{- end }}
    {{- with $pt.affinity }}
    affinity:
      {{- toYaml . | nindent 6 }}
    {{- end }}
    {{- with $pt.tolerations }}
    tolerations:
      {{- toYaml . | nindent 6 }}
    {{- end }}
    {{- with $pt.topologySpreadConstraints }}
    topologySpreadConstraints:
      {{- toYaml . | nindent 6 }}
    {{- end }}
{{- end }}
{{- if $hasVCL }}
volumeClaimTemplate:
  spec:
    {{- if $vcl.storageClassName }}
    storageClassName: {{ $vcl.storageClassName | quote }}
    {{- end }}
    resources:
      requests:
        storage: {{ default "16Gi" $vcl.storage | quote }}
{{- end }}
{{- end -}}

# 1 · Шпаргалка: kubectl, манифесты, Helm | short: Шпаргалка | kind: ref
**Посмотреть**

| Что | Команда |
|---|---|
| объекты | `kubectl get pods\|deploy\|svc\|ingress\|pvc\|events -n <ns>`, `-A` — все namespace, `-o wide`, `-o yaml`, `-w` — следить |
| подробности и события | `kubectl describe <тип> <имя>` |
| логи | `kubectl logs <pod>`, `-f`, `--previous`, `-c <контейнер>`, `-l app=…`, `--since=10m` |
| в контейнер | `kubectl exec -it <pod> -- sh`, `kubectl debug` |
| нагрузка | `kubectl top nodes`, `kubectl top pods` |
| поля объекта | `kubectl explain deployment.spec.strategy` |
| список типов | `kubectl api-resources` |
| контекст и namespace | `kubectl config current-context`, `kubectl config set-context --current --namespace=dev` |

**Изменить**

| Что | Команда |
|---|---|
| применить файл | `kubectl apply -f file.yaml` (или папку, `-k` для kustomize) |
| что изменится | `kubectl diff -f file.yaml` |
| удалить | `kubectl delete -f file.yaml`, `kubectl delete pod <имя>` |
| масштаб | `kubectl scale deploy/<имя> --replicas=3` |
| образ | `kubectl set image deploy/<имя> <контейнер>=<образ>:<тег>` |
| обновление | `kubectl rollout status\|history\|undo\|restart deploy/<имя>` |
| ждать | `kubectl wait --for=condition=Ready pod -l app=… --timeout=60s` |
| порт на Mac | `kubectl port-forward svc/<имя> 8080:80` |
| права | `kubectl auth can-i <verb> <ресурс> --as=<кто> -n <ns>` |

**Каркас манифеста**

| Объект | Ключевые поля |
|---|---|
| Pod | `spec.containers[].image`, `ports`, `env`, `resources`, `readinessProbe`, `livenessProbe`, `securityContext` |
| Deployment | `spec.replicas`, `selector.matchLabels` (= `template.metadata.labels`), `strategy.rollingUpdate.maxSurge/maxUnavailable` |
| Service | `spec.selector`, `ports[].port/targetPort`, `type` (`ClusterIP`, `NodePort`, `LoadBalancer`) |
| Ingress | `ingressClassName`, `rules[].host`, `http.paths[].path/pathType/backend.service` |
| PVC | `accessModes`, `resources.requests.storage`, `storageClassName` |
| StatefulSet | `serviceName`, `volumeClaimTemplates` |
| ConfigMap / Secret | `data` / `stringData`, подключение: `envFrom`, `env[].valueFrom`, `volumes` |
| HPA | `scaleTargetRef`, `minReplicas`, `maxReplicas`, `metrics[].resource.target.averageUtilization` |
| NetworkPolicy | `podSelector`, `policyTypes`, `ingress[].from`, `ports` |
| Role / RoleBinding | `rules[].apiGroups/resources/verbs`, `subjects`, `roleRef` |

**Helm**

| Что | Команда |
|---|---|
| репозитории | `helm repo add\|update\|list`, `helm search repo <слово>` |
| значения chart’а | `helm show values <chart>` |
| репетиция | `helm lint <chart>`, `helm template <имя> <chart> -f values.yaml --debug` |
| установка и обновление | `helm upgrade --install <имя> <chart> -n <ns> --create-namespace -f values-prod.yaml --atomic --wait --timeout 5m` |
| статус и журнал | `helm list -A`, `helm status <имя>`, `helm history <имя>` |
| что применено | `helm get values\|manifest <имя>` |
| откат и удаление | `helm rollback <имя> <ревизия>`, `helm uninstall <имя>` |
| упаковка | `helm package <chart>`, `helm repo index <папка> --url …`, `helm dependency update` |
| проверка | `helm test <имя>`, `helm diff upgrade …` (плагин) |

**Синтаксис шаблонов**

| Конструкция | Смысл |
|---|---|
| `{{ .Values.x }}`, `{{ .Release.Name }}`, `{{ .Chart.Name }}` | подстановки; `$` — корень внутри `with`/`range` |
| `{{- ... -}}` | убрать пробелы и переводы строк слева / справа |
| `{{ if .Values.x }} … {{ else }} … {{ end }}` | условие (пусто = ложь) |
| `{{ with .Values.x }} … {{ end }}` | работать внутри значения |
| `{{ range .Values.list }} {{ . }} {{ end }}` | цикл |
| `{{ .Values.x \| default "v" \| quote }}` | конвейер |
| `{{ toYaml .Values.res \| nindent 12 }}` | вставить блок с отступом |
| `{{ required "сообщение" .Values.x }}` | обязательное значение |
| `{{ include "chart.helper" . \| nindent 4 }}` | вызов именованного шаблона |

**kind**

| Что | Команда |
|---|---|
| создать / удалить кластер | `kind create cluster --name <имя> --config kind-config.yaml --image kindest/node:v1.37.0`, `kind delete cluster --name <имя>` |
| образ с Mac в узлы | `kind load docker-image <образ> --name <имя>` |
| список | `kind get clusters` |

# 2 · Справочник ошибок: симптом → причина → что делать | short: Справочник ошибок | kind: ref
Диагностика идёт по цепочке сверху вниз: **манифест принят → Pod запланирован → образ скачан → контейнер стартовал → проба готовности прошла → Service нашёл Pod → Ingress нашёл Service → приложение отвечает**. Главная команда любого разбора — `kubectl describe` и раздел `Events` в конце вывода.

**Состояния Pod**

| Статус | Причина | Что делать |
|---|---|---|
| `Pending` | нет места на узлах (`Insufficient cpu/memory`), PVC не привязан, нет узла под `nodeSelector`/taint | `describe pod` → `Events`; PVC → шаг 6.7 |
| `ContainerCreating` долго | образ качается, том не монтируется, нет Secret/ConfigMap | `describe pod` → `Events` |
| `ImagePullBackOff` / `ErrImagePull` | неверный образ или тег, приватный реестр без `imagePullSecrets` | имя и тег; для `kind` — `kind load docker-image` (3.7) |
| `ErrImageNeverPull` | `imagePullPolicy: Never`, а образа нет на узле | `kind load docker-image` (3.7) |
| `CrashLoopBackOff` | контейнер стартует и падает | `kubectl logs --previous`; код выхода в `describe` |
| `OOMKilled` (в `describe`, `Last State`) | память выше `limits` | поднять `limits` или найти утечку (8.3) |
| `CreateContainerConfigError` | нет ключа/объекта в Secret или ConfigMap; `runAsNonRoot` и образ от root | `describe pod`; имена ключей буквально (7.7, 9.3) |
| `Error: … violates PodSecurity` | namespace с `restricted`/`baseline` | `securityContext` (9.4) |
| `Evicted` | узел перегружен (память/диск) | `describe node`, ресурсы |
| `Terminating` вечно | финалайзер или недоступный узел | `kubectl get pod -o yaml` → `finalizers`; `--grace-period=0 --force` — крайняя мера |
| `0/1 Running` | не проходит `readinessProbe` | путь и порт пробы, логи (8.2) |

**Сеть и доступ**

| Симптом | Причина | Что делать |
|---|---|---|
| `Service` есть, `endpoints` пуст | `selector` не совпадает с метками Pod; Pod не `Ready` | `kubectl get endpoints`; метки (2.4, 3.4) |
| `502`/`503` от Ingress | нет живых Pod, неверный `targetPort`, неверное имя Service | `describe ingress`, `get endpoints` (5.7) |
| `404 page not found` (Traefik) | роутер не нашёл `Host`/путь | `describe ingress`, `ingressClassName` |
| `connection refused` к `localhost:80` | не проброшены порты `kind`, не запущен Traefik | `extraPortMappings` (5.6) |
| `no such host` внутри кластера | имя Service с опечаткой или другой namespace | `<svc>.<ns>.svc.cluster.local` (5.3) |
| `NetworkPolicy` «не действует» | CNI не применяет политики или политика выбрала пустое множество | `kubectl get pods -l <селектор>`; проверка `wget` изнутри (9.5, 9.7) |
| `Unable to connect to the server` | кластер не поднят или контекст не тот | `kubectl config current-context`, `kind get clusters` (1.8) |

**Применение манифестов**

| Симптом | Причина | Что делать |
|---|---|---|
| `error: unable to recognize … no matches for kind` | опечатка в `kind`/`apiVersion` или нет CRD | `kubectl api-resources` (2.7) |
| `selector does not match template labels` | `matchLabels` ≠ `template.metadata.labels` | выровнять метки (4.1) |
| `field is immutable` | меняется неизменяемое поле (`selector`, `storageClassName`…) | пересоздать объект |
| `error validating … unknown field` | отступы или поле не на своём уровне | `kubectl explain <путь>` |
| `forbidden: User "…" cannot …` | не хватает прав RBAC | `kubectl auth can-i … --as=…` (9.1) |
| `x509: certificate signed by unknown authority` | `kubeconfig` от другого кластера или нет CA | проверить контекст |
| `exceeded quota` | `ResourceQuota` namespace (8.1) | `describe quota`, снизить запросы |

**Helm**

| Симптом | Причина | Что делать |
|---|---|---|
| `YAML parse error`, `error converting YAML to JSON` | неверный отступ после `nindent`, пропущенный пробел | `helm template --debug`, читать готовый YAML (12.7, 13.8) |
| `nil pointer evaluating interface {}.x` | нет такого ключа в values | `helm template --debug`, регистр, уровень |
| `INSTALLATION FAILED: … exists and cannot be imported` | объект создан не Helm | другой namespace/имя или `kubectl delete` |
| `another operation … is in progress` | зависший `pending-upgrade` | `helm rollback`, затем крайняя мера (14.7) |
| `UPGRADE FAILED: timed out waiting for the condition` | Pod не стали готовы | `kubectl get pods`, `describe`; `--atomic` откатит сам |
| `Error: found in Chart.yaml, but missing in charts/` | зависимости не скачаны | `helm dependency update` |
| `values don't meet the specifications of the schema` | значения не прошли схему chart’а | сообщение называет поле |
| релиз «живой», а изменения не видны | забыт `-f` или `--set` при `upgrade` | `helm get values <имя>` |

**Автомасштабирование и мониторинг**

| Симптом | Причина | Что делать |
|---|---|---|
| HPA: `<unknown>/50%` | нет `metrics-server` или нет `requests.cpu` | `kubectl top pods`; `describe hpa` (10.7) |
| `kubectl top` → `Metrics API not available` | `metrics-server` не готов | `--kubelet-insecure-tls` в `kind` (10.2) |
| Реплики растут, Pod’ы `Pending` | узлам не хватает ресурсов | разгрузить или добавить узлы |
| Панель Grafana пуста | не тот источник, диапазон времени, метки | `count(метрика)` в Prometheus (11.7) |
| Цель Prometheus не появилась | метка `ServiceMonitor` не совпала с `Service`, у порта нет имени | `kubectl get servicemonitor -A` (11.4) |

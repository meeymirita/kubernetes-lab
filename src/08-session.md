# Сессия 8 · Эксплуатация и диагностика
dur: ~4 ч

## 8.1 Namespace: dev/prod и квоты | short: Namespace и квоты | est: ~35 мин
### intro
**Слова шага:** *namespace*, *`ResourceQuota`*, *`LimitRange`*, *переключение контекста*.

:::tip Если совсем просто
Namespace — это отдельные квартиры в одном доме (кластере): у каждой свои жильцы (объекты) с одинаковыми именами, которые не путаются друг с другом («db» в квартире `dev` — не та же db, что в квартире `prod»). `ResourceQuota` — общий лимит счётчика на электричество для всей квартиры, `LimitRange` — правило «на одну розетку не больше N ватт» для каждого отдельного прибора.
:::

```bash run
kubectl create namespace dev
kubectl create namespace prod
kubectl get namespaces
kubectl config set-context --current --namespace=dev
kubectl config view --minify | grep namespace
```

### result
```out auto
```

Большинство объектов (Pod, Deployment, Service, ConfigMap, Secret) — **namespaced** (существуют внутри конкретного namespace); немногие — **cluster-scoped** (Node, PersistentVolume, Namespace сам, ClusterRole — сессия 9.1): их имена уникальны на весь кластер. `kubectl config set-context --current --namespace=dev` меняет **namespace по умолчанию** для текущего контекста — без `-n` каждой команде; `kubectl get pods -A` (или `--all-namespaces`) покажет объекты из всех namespace сразу.

Квоты на namespace `prod` (учебный пример, не применяем на свой стек — он пока живёт в `default`):

```yaml
apiVersion: v1
kind: ResourceQuota
metadata: {name: prod-quota, namespace: prod}
spec:
  hard:
    requests.cpu: "4"
    requests.memory: 4Gi
    limits.cpu: "8"
    limits.memory: 8Gi
    pods: "20"
---
apiVersion: v1
kind: LimitRange
metadata: {name: prod-limits, namespace: prod}
spec:
  limits:
    - type: Container
      default: {cpu: 200m, memory: 256Mi}
      defaultRequest: {cpu: 100m, memory: 128Mi}
```

### why
`ResourceQuota` — лимит на **весь namespace суммарно** (не даст создать 21-й Pod или превысить 4 CPU запросов всеми Pod вместе); `LimitRange` — умолчания и границы **для каждого отдельного** контейнера (если забыла указать `requests`/`limits` у контейнера — применится значение по умолчанию из `LimitRange`, вместо того чтобы контейнер остался совсем без ограничений). Вместе они не дают одному namespace (команде, проекту) съесть ресурсы всего кластера.

### deep Если не получилось
- **`kubectl get pods` вдруг «ничего не показывает»** — проверь текущий namespace (`kubectl config view --minify | grep namespace`): возможно, ты переключилась на `dev`, а искомые Pod лежат в `default`.

### quiz
- Чем cluster-scoped объекты отличаются от namespaced по уникальности имён?
- В чём разница между `ResourceQuota` и `LimitRange`?
- Как посмотреть объекты из всех namespace одной командой?

### links
- https://kubernetes.io/docs/concepts/overview/working-with-objects/namespaces/ | Namespace | Kubernetes: Namespaces
- https://kubernetes.io/docs/concepts/policy/resource-quotas/ | ResourceQuota | Kubernetes: Resource Quotas

## 8.2 Probes: readiness, liveness, startup | short: Пробы здоровья | est: ~45 мин
### intro
**Слова шага:** *readiness probe*, *liveness probe*, *startup probe*, *`initialDelaySeconds`*, *`periodSeconds`*, *`failureThreshold`*.

:::tip Если совсем просто
Три разных вопроса к сотруднику. **Startup probe** — «ты уже вообще пришла на работу и разложила вещи?» (спрашивается только в начале, пока не ответит «да» — остальные пробы не беспокоят). **Readiness probe** — «ты готова принимать посетителей прямо сейчас?» (временное «нет» — нормально: обедает, ждёт поставку — просто не присылай к ней людей в этот момент, не увольняй). **Liveness probe** — «ты вообще в сознании?» (если долго не отвечает — это не «занята», это «что-то серьёзно не так», и Kubernetes её «перезапускает», то есть убивает контейнер и поднимает заново).
:::

```bash run
kubectl patch deployment coffeeshop-api --type=strategic -p '
spec:
  template:
    spec:
      containers:
        - name: api
          readinessProbe:
            httpGet: {path: /health, port: 3000}
            initialDelaySeconds: 3
            periodSeconds: 5
            failureThreshold: 3
          livenessProbe:
            httpGet: {path: /health, port: 3000}
            initialDelaySeconds: 10
            periodSeconds: 10
            failureThreshold: 3
'
kubectl rollout status deployment/coffeeshop-api
kubectl get pods -l app=coffeeshop-api
```

### result
```out auto
```

`READY` в `kubectl get pods` теперь показывает **и фазу, и готовность** (`1/1` — контейнер `Running` и проба готовности прошла; `0/1` — `Running`, но ещё/уже не готов). Это ровно то, от чего зависит, попадёт ли Pod в `endpoints` Service (сессия 3.4) — **не готовый Pod не получает трафик**, даже если он `Running`.

Проверим `livenessProbe` в деле — заставим `/health` временно отвечать ошибкой (используем встроенный в CoffeeShop API эндпоинт `/flaky` из `starter/`, который можно включить в «нездоровый» режим):

```bash run
kubectl exec deploy/coffeeshop-api -- curl -s -X POST localhost:3000/drop 2>&1 | head -3
sleep 25
kubectl get pods -l app=coffeeshop-api
kubectl describe pod -l app=coffeeshop-api | grep -A2 Liveness
```

### result
```out auto
```

После нескольких неудачных проверок подряд (`failureThreshold: 3`, период 10 секунд — то есть около 30 секунд) `kubelet` перезапускает контейнер (счётчик `RESTARTS` у Pod увеличился) — это и называют **crash-тестом**: мы искусственно «заболели» и увидели самолечение в действии.

### why
`readinessProbe` без `livenessProbe` — Pod может висеть «не готов» вечно, но хотя бы не получает лишний трафик. `livenessProbe` без `readinessProbe` — Pod может получать трафик, даже будучи фактически неработоспособным, пока не сработает перезапуск. Используй обе вместе, с разными (обычно более терпимыми у liveness) порогами — не копируй одну и ту же пробу под оба поля бездумно.

### deep startupProbe — зачем отдельно
Для приложений с долгим стартом (прогрев кэша, миграции при запуске) `startupProbe` даёт **больше времени** именно на старт, не ослабляя при этом чувствительность `livenessProbe` после старта (без неё пришлось бы ставить большой `initialDelaySeconds` у liveness, теряя быстроту реакции на реальное зависание уже работающего приложения).

### deep Если не получилось
- **Pod то готов, то не готов без видимой причины** — проверь `periodSeconds`/`failureThreshold`: слишком агрессивные настройки (частые проверки, низкий порог) могут давать «дрожание» готовности при кратковременных задержках приложения.

### quiz
- На какой из трёх проб зависит попадание Pod в endpoints Service?
- Что Kubernetes делает при провале `livenessProbe`, в отличие от провала `readinessProbe`?
- Для чего нужен отдельный `startupProbe`, если можно просто увеличить `initialDelaySeconds` у `livenessProbe`?

### links
- https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#container-probes | пробы контейнера | Kubernetes: Container Probes
- https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/ | настройка проб | Kubernetes: Configure Probes

## 8.3 requests, limits и OOMKilled | short: requests и limits | est: ~35 мин
### intro
**Слова шага:** *`requests`*, *`limits`*, *`OOMKilled`*, *QoS-класс (`Guaranteed`/`Burstable`/`BestEffort`)*.

:::tip Если совсем просто
`requests` — это то, что ты **гарантированно бронируешь** за столиком в кофейне (столик твой, даже если сейчас не используешь его целиком). `limits` — потолок, больше которого тебе просто не дадут занять, даже если соседние столики свободны. Если по CPU превышение `limits` просто «притормаживает» (как разговор на пониженной громкости), то по памяти превышение `limits` — это принудительное выселение: `OOMKilled`, контейнер убивают мгновенно.
:::

```bash run
kubectl patch deployment coffeeshop-api --type=strategic -p '
spec:
  template:
    spec:
      containers:
        - name: api
          resources:
            requests: {cpu: 100m, memory: 128Mi}
            limits: {cpu: 500m, memory: 256Mi}
'
kubectl rollout status deployment/coffeeshop-api
kubectl describe nodes | grep -A5 "Allocated resources"
```

### result
```out auto
```

- **`requests`** — используется **scheduler**'ом (сессия 2.1) при выборе узла: Pod попадёт только на узел, у которого есть **свободные** столько-то CPU/памяти (из общего «бюджета» узла, за вычетом уже забронированного другими Pod).
- **`limits`** — жёсткий потолок **на уже работающий** контейнер: превышение CPU-лимита — throttling (контейнер просто замедляется); превышение лимита **памяти** — контейнер немедленно убивается (`OOMKilled`), без шансов «подождать, вдруг отпустит» (память, в отличие от CPU, нельзя временно «одолжить»).

Воспроизведём `OOMKilled` специально:

```bash run
kubectl run oom-test --image=polinux/stress --limits=memory=50Mi --requests=memory=50Mi --restart=Never -- stress --vm 1 --vm-bytes 150M --vm-hang 0
sleep 5
kubectl get pod oom-test
kubectl describe pod oom-test | grep -A3 "Last State"
kubectl delete pod oom-test
```

### result
```out auto
```

Статус покажет `OOMKilled` в `Last State` — контейнер пытался занять 150 МБ при лимите 50 МБ и был убит ядром Linux (`cgroup` отследил превышение).

**QoS-классы** (назначаются автоматически, не задаются вручную): **`Guaranteed`** — `requests` **равны** `limits` у всех контейнеров Pod (самый высокий приоритет при нехватке ресурсов на узле); **`Burstable`** — `requests` заданы, но меньше `limits` (как у нашего API выше); **`BestEffort`** — ни `requests`, ни `limits` не заданы вовсе (первый кандидат на вытеснение при нехватке ресурсов на узле).

### why
«Pod внезапно перезапускается без видимой ошибки в коде» — классика для `OOMKilled`: приложение не «упало сама», её принудительно остановили за превышение памяти. Проверка `describe` → `Last State: Terminated, Reason: OOMKilled` отличает это от обычного краша приложения и направляет решение в другую сторону — повысить `limits` или найти утечку памяти, а не искать баг в логике.

### deep Если не получилось
- **Узел полностью занят, Pod не планируется (`Pending`, `Insufficient cpu`)** — сумма `requests` всех Pod на узле уже достигла лимита узла; добавь узел (`kind` — пересоздать кластер с большим числом worker), снизь `requests`, или удали неиспользуемые Pod.

### quiz
- Чем поведение при превышении `limits.cpu` отличается от превышения `limits.memory`?
- Для чего scheduler использует `requests`, а не `limits`, при выборе узла?
- Какой QoS-класс у Pod с `requests` равными `limits` у всех контейнеров?

### links
- https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/ | управление ресурсами контейнеров | Kubernetes: Resource Management for Pods and Containers
- https://kubernetes.io/docs/tasks/configure-pod-container/quality-service-pod/ | QoS-классы | Kubernetes: Configure Quality of Service for Pods

## 8.4 initContainer, Job, CronJob | short: initContainer и Job | est: ~35 мин
### intro
**Слова шага:** *`initContainer`*, *Job*, *`restartPolicy: OnFailure`*, *`completions`/`parallelism`*.

:::tip Если совсем просто
`initContainer` — это швейцар, который должен закончить свою работу и уйти, прежде чем откроются двери для основных контейнеров (например, убедиться, что база данных уже отвечает). Job — это разовое поручение «сделать и отчитаться», а не постоянная служба — в отличие от Deployment, у Job есть понятие «готово» и он не пытается запуститься заново после успеха.
:::

**initContainer** — ждём готовности БД перед стартом API (защита от гонки при холодном старте всего стека):

```yaml
spec:
  template:
    spec:
      initContainers:
        - name: wait-for-db
          image: busybox:1.36
          command: ["sh", "-c", "until nc -z db 5432; do echo waiting for db; sleep 2; done"]
      containers:
        - name: api
          image: coffeeshop-api:v1
```

`initContainer`'ы выполняются **по очереди**, **до** старта обычных контейнеров Pod; если `initContainer` завершается с ошибкой — Pod повторяет **весь** цикл `initContainer`'ов (с учётом `restartPolicy`), а основные контейнеры не стартуют вовсе.

**Job** — одноразовая задача:

```bash run
kubectl apply -f - <<'EOF'
apiVersion: batch/v1
kind: Job
metadata: {name: db-migrate}
spec:
  completions: 1
  backoffLimit: 3
  template:
    spec:
      restartPolicy: OnFailure
      containers:
        - name: migrate
          image: postgres:18
          command: ["psql", "-h", "db", "-U", "coffeeshop", "-d", "coffeeshop", "-c", "SELECT 1;"]
          env:
            - {name: PGPASSWORD, valueFrom: {secretKeyRef: {name: db-credentials, key: POSTGRES_PASSWORD}}}
EOF
kubectl wait --for=condition=complete job/db-migrate --timeout=30s
kubectl get job db-migrate
kubectl delete job db-migrate
```

### result
```out auto
```

`restartPolicy: OnFailure` (не `Always`, как у обычных Pod) — при ошибке контейнер перезапускается **внутри того же Pod**, до `backoffLimit` попыток; после успеха (`completions` достигнуто) Job считается `Complete` и больше ничего не делает. `CronJob` (обзор был в сессии 6.6) — это просто Job, который Kubernetes создаёт заново **по расписанию**.

### why
Это закрывает последний пробел перед тем, как считать CoffeeShop полностью «эксплуатируемым»: разовые задачи (миграции схемы БД, разовая очистка, резервная копия) не должны жить как бесконечный Deployment — Job честно сообщает «сделано» и не пытается перезапуститься после успеха.

### deep Если не получилось
- **Job висит, не завершается** — `backoffLimit` исчерпан при постоянных ошибках: `kubectl describe job` покажет причину через связанные Pod (`kubectl get pods -l job-name=db-migrate`).

### quiz
- Что происходит с основными контейнерами Pod, если `initContainer` завершился с ошибкой?
- Чем `restartPolicy: OnFailure` у Job отличается от поведения обычного Deployment?
- Как CronJob связан с Job?

### links
- https://kubernetes.io/docs/concepts/workloads/pods/init-containers/ | initContainer | Kubernetes: Init Containers
- https://kubernetes.io/docs/concepts/workloads/controllers/job/ | Job | Kubernetes: Job

## 8.5 Dashboard и k9s | short: Dashboard и k9s | est: ~20 мин
### intro
**Слова шага:** *Kubernetes Dashboard*, *`k9s`*, *терминальный интерфейс*.

:::tip Если совсем просто
`kubectl` — это печатная машинка: точно, но по одной команде за раз. `k9s` — пульт с множеством кнопок прямо в терминале: списки объектов, логи, `exec`, удаление — всё с клавиатуры, без повторного набора имён. Dashboard — то же самое, но в браузере, для тех, кому привычнее мышь.
:::

```bash run
brew install derailed/k9s/k9s 2>&1 | tail -3
```

`k9s` запускается командой `k9s` прямо в терминале (интерактивный интерфейс — не выполняется в автоматическом прогоне методички, пробуй сама): список Pod по namespace, `l` — логи выбранного, `d` — describe, `s` — shell внутрь, `:deploy` — переключиться на Deployment. Это не замена `kubectl` (под капотом он вызывает те же API-запросы), а более быстрый способ **осматриваться**.

**Веб-дашборд** — отдельный официальный Helm chart (`kubernetes-dashboard`), требует отдельной настройки доступа (ServiceAccount с токеном — связь с RBAC из сессии 9.1); в учебном `kind`-кластере проще и быстрее пользоваться `k9s` или `kubectl`.

### result
Команды для реального использования `k9s` — интерактивные (не автоматизируются в прогоне методички); убедись, что `k9s` установился (`k9s version`), и попробуй сама: `k9s` → `:pods` → выбери CoffeeShop API → `l` для логов → `Esc` для выхода.

### why
Для ежедневной работы с кластером (не для скриптов и CI — там всегда `kubectl`) `k9s` экономит огромное количество времени: не нужно помнить имена Pod, чтобы посмотреть логи — выбор стрелками и одна буква.

### quiz
- Чем `k9s` отличается от `kubectl` по уровню (использует другой API или тот же)?
- Для какой разновидности задач (разовая проверка руками или автоматизация в CI) больше подходит `k9s`?

### links
- https://k9scli.io/ | k9s | k9s: Documentation
- https://kubernetes.io/docs/tasks/access-application-cluster/web-ui-dashboard/ | веб-дашборд | Kubernetes: Web UI (Dashboard)

## 8.6 Диагностика: таблица статус → причина | short: Таблица диагностики | est: ~30 мин
### intro
**Слова шага:** *сводная таблица статусов*, *`kubectl debug`*, *порядок диагностики*.

:::tip Если совсем просто
Приёмный покой не лечит по одной догадке — он сортирует по симптому в таблицу «температура высокая → к терапевту, кровь → к хирургу». У Kubernetes такая же таблица есть, просто её нужно прочитать один раз и дальше распознавать по памяти.
:::

```svg
@diagnosis-tree
```

| Статус Pod | Типичная причина | Где смотреть | Сессия |
|---|---|---|---|
| `Pending` (долго) | не хватает ресурсов узла, нет подходящего узла, PVC не привязан | `describe` → Events | 2.2, 6.7 |
| `ImagePullBackOff` / `ErrImagePull` | неверный тег/имя образа, нет доступа к registry | `describe` → Events | 3.7 |
| `ErrImageNeverPull` | `imagePullPolicy: Never`, образа нет локально | `describe` → Events | 3.7 |
| `CreateContainerConfigError` | ссылка на несуществующий ключ ConfigMap/Secret | `describe` → Events | 7.7 |
| `CrashLoopBackOff` | приложение стартует и падает | `logs --previous`, `describe` | 4.7 |
| `OOMKilled` (в `Last State`) | контейнер превысил `limits.memory` | `describe` → Last State | 8.3 |
| `Running`, но `0/1` в READY | не проходит `readinessProbe` | `describe` → Events/Conditions | 8.2 |
| `Evicted` | узел исчерпал ресурсы (диск/память), Pod вытеснен | `describe`, `kubectl get events -A` | — |
| `Unknown` | `kubelet` узла не отвечает control plane | `kubectl get nodes` | 2.1 |

**`kubectl debug`** — последний инструмент на крайний случай: когда у контейнера нет шелла (минимальный/distroless образ, сессия 3.3) или нужно посмотреть на Pod «снаружи», не трогая его:

```bash run
kubectl debug -it coffeeshop-api-<под-реальным-именем> --image=busybox:1.36 --target=api -- sh
```

`--target` подключается к **тем же namespace процессов**, что у целевого контейнера — можно смотреть его процессы (`ps`) изнутри вспомогательного контейнера, даже если у оригинального нет собственного шелла.

### result
Таблицу выше держи под рукой весь оставшийся курс — она же почти целиком войдёт в справочник ошибок лабы (`ref-93-errors.md`).

### why
Большая часть реальной работы с Kubernetes — это именно распознавание статусов по таблице, а не написание нового кода. Чем быстрее статус превращается в конкретную гипотезу, тем быстрее починка.

### deep Если не получилось
- **Статус не из таблицы** — `kubectl describe` почти всегда даёт достаточно текста для поиска в документации буквально по фразе из Events.

### quiz
- Назови три статуса Pod, которые означают «контейнер даже не пытался стартовать», в отличие от «стартовал и упал».
- Для чего нужен `kubectl debug --target`, если у контейнера и так есть шелл?

### links
- https://kubernetes.io/docs/tasks/debug/debug-application/determine-reason-pod-failure/ | причины отказа Pod | Kubernetes: Determine the Reason for Pod Failure
- https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/#ephemeral-container | эфемерные контейнеры и kubectl debug | Kubernetes: Ephemeral Containers

## 8.7 🔨 Production Hell 1: пять поломок | short: 🔨 Production Hell 1 | est: ~45 мин
### intro
**Слова шага:** *многослойная поломка*, *диагностика без подсказок, где именно*.

:::tip Если совсем просто
На этот раз подсказки, какая именно поломка где — не будет: пять независимых проблем раскиданы по стеку, как в настоящей смене дежурного инженера, когда звонят «сайт не работает» и больше ничего не говорят. Твой чеклист из шага 7.6 и таблица из шага 8.6 — единственное снаряжение.
:::

```bash run
cd ~/kubernetes-lab
kubectl apply -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata: {name: hell-web}
spec:
  replicas: 2
  selector: {matchLabels: {app: hell-web}}
  template:
    metadata: {labels: {app: hell-web2}}
    spec:
      containers:
        - name: web
          image: nginx:alpine
---
apiVersion: v1
kind: Service
metadata: {name: hell-api}
spec:
  selector: {app: hell-api}
  ports: [{port: 80, targetPort: 9999}]
---
apiVersion: apps/v1
kind: Deployment
metadata: {name: hell-api}
spec:
  replicas: 2
  selector: {matchLabels: {app: hell-api}}
  template:
    metadata: {labels: {app: hell-api}}
    spec:
      containers:
        - name: api
          image: coffeeshop-api:v1
          resources: {limits: {memory: 20Mi}}
          env:
            - {name: SECRET_X, valueFrom: {secretKeyRef: {name: no-such-secret, key: x}}}
EOF
kubectl get deploy,pod -l 'app in (hell-web,hell-api)'
```

### result
```out auto
```

Пять поломок закопаны в эти манифесты (раскрывай по одной, сверяясь с таблицей 8.6, а не глядя сюда сразу): (1) `hell-web` — `selector.matchLabels: app: hell-web`, а `template.metadata.labels: app: hell-web2` — манифест даже не применится валидатором (`selector does not match template labels`, сессия 4.1); (2) `hell-api` Service ссылается на `targetPort: 9999`, а приложение слушает `3000` — `endpoints` будет не пуст, но запросы получат `502`; (3) `SECRET_X` ссылается на несуществующий Secret `no-such-secret` — `CreateContainerConfigError` (сессия 7.7); (4) `limits.memory: 20Mi` — заведомо мало для Node.js-приложения, которое после старта сразу получит `OOMKilled` (сессия 8.3); (5) (скрытая — проверь сама) у `hell-api` нет `readinessProbe` вовсе, значит Service будет слать трафик, не дожидаясь реальной готовности приложения — проверь это, добавив пробу и сравнив поведение до/после.

**Задание:** исправь все пять, используя только `kubectl describe`/`get events`/таблицу из шага 8.6 — без подсказок свыше того, что уже дано здесь. После починки:

```bash run
kubectl get deploy,pod -l 'app in (hell-web,hell-api)'
kubectl delete deploy hell-web hell-api
kubectl delete svc hell-api
```

### result
```out auto
```

### why
Это сессия закрывается именно так специально: пять одновременных, не связанных друг с другом причин — ближе к тому, что реально происходит при инциденте, чем аккуратный «один шаг — одна поломка» из предыдущих шагов. Умение **не путать** причины друг с другом (не чинить OOMKilled, думая, что дело в Secret) — то, что отличает уверенную диагностику от угадывания.

### deep Если не получилось
- **Запуталась, какая поломка от какой** — чини по одной, проверяя `kubectl get pods` после каждого исправления: статус должен **меняться**, а не оставаться тем же — если после правки статус не изменился, значит, ты поправила не ту причину или есть вторая проблема на этом же объекте.

### quiz
- Почему `hell-web` даже не создастся как Deployment, пока ты не поправишь labels?
- Как отличить «порт неверный у Service» (502) от «образа нет» (ImagePullBackOff) по симптому?
- Почему отсутствие `readinessProbe` опаснее всего именно в момент старта, а не постоянно?

### links
- https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/ | отладка Pod (сводка) | Kubernetes: Debug Running Pods

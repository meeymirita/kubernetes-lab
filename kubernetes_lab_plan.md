# 🧪 Kubernetes и Helm — большая лаба

> Исходный список (13 разделов, ~120 пунктов из интернета) — в истории git, коммит `d6104a5`. Общие правила — `plan/README.md` родительского репозитория `anitech-performance`: режимы «с нуля»/«продолжение», **стандарт подробности («каждое слово объяснено»)**, размер.

> **Обновлено 18.10.2026 (после переписывания Traefik-лабы):** предзнания и вход пересмотрены — см. раздел «Предзнания и вход» ниже. Ворота очерёдности выполнены: у Traefik-лабы есть проверенный `starter/` (шаг 10.5). Старая `kubernetes.html` пока на сайте без изменений.

**Место в последовательности: №4 из 5** (после Traefik); общий порядок прохождения и создания — `plan/README.md`, раздел «Последовательность работ».

## Что делаем с готовой лабой
Готовая `kubernetes.html` (3 сессии, ~10 ч) **переписывается в большую** (13 сессий, ~52 ч) в том же репозитории; Helm входит в неё. Сохраняется ядро (kind, Pod → Deployment → Service, ConfigMap/Secret, PVC, probes, Traefik как Ingress, HPA). Добавляются азбука, разбор каждого слова, namespace, rollout/rollback, Job/CronJob, StatefulSet, безопасность и весь Helm. Жёсткая зависимость готовой лабы от кода Traefik-лабы **снимается**: стек CoffeeShop лежит в `starter/` (сессия 10 Traefik-лабы, шаг 10.5); старый образ `traefik-lab-api:v1` больше не создаётся — новая лаба строит `coffeeshop-api:v1` из `starter/coffeeshop/api`.

## Паспорт

| | |
|---|---|
| Режим | **продолжение Traefik-лабы** (её итоговая папка `starter/`: стек CoffeeShop за Traefik, `up.sh`, `smoke.sh`, `monitoring/`) **или самостоятельная** (та же `starter/` берётся готовой; Docker и Compose объясняются в сессии 1 в нужном объёме) |
| Размер | 13 сессий × ~4 ч = **~52 ч**, ~90 шагов |
| Сквозной проект | **CoffeeShop в Kubernetes**: API + frontend + PostgreSQL 18 + Adminer; в конце — собственный Helm chart |
| Версии | kind v0.33 / Kubernetes 1.37 (как в готовой лабе), Helm — актуальная мажорная (**сверьтесь: на конец 2025 вышел Helm 4**) |
| Решения | кластер — **kind** (вместо Minikube из исходного плана: легче и быстрее для ноутбука); Ingress Controller — **Traefik v3.7** (`ingress-nginx` объявлен выводимым из поддержки, по объявлению SIG Network — **сверьтесь**); модель «роутер → middleware → сервис» уже известна из Traefik-лабы |
| Ограничение | kind-кластеры греют ноутбук; Docker Desktop — только с согласия; перед тяжёлыми прогонами предупреждать |

## Предзнания и вход (обновлено 18.10.2026)

**Что надо знать до старта.** Лаба — не «Kubernetes с нуля вообще», а **миграция уже знакомого стека**. Поэтому нужны два блока знаний:

| Что | Откуда | Где нужно в этой лабе | Статус |
|---|---|---|---|
| Образ, контейнер, `Dockerfile`, слои, registry (`kind load docker-image`) | Docker-лаба, сессии 3–5, 10 | сессия 3 (образ API в Pod), сессия 8 (безопасность контейнера) | **знания** (минимум — шаг 1.3) |
| Сети и порты Docker, Compose (`depends_on`, `healthcheck`, тома, `.env`) | Docker-лаба, сессии 6–9 | Service и DNS (3), probes (6), PVC (7), ConfigMap/Secret (6) | **знания** |
| Reverse proxy, роутер → middleware → сервис, метки, правила и приоритеты | Traefik-лаба, сессии 1–4 | Traefik как Ingress-контроллер (5), `IngressRoute` и Middleware CRD | **желательно**; без неё модель объясняется в сессии 5 заново и дольше |
| `healthcheck`, балансировка, canary, rateLimit, retry, circuitBreaker | Traefik-лаба, сессии 5–6 | probes и rollout (4, 6), canary и weighted-сервис (12) | желательно |
| TLS: mkcert, mTLS, ACME | Traefik-лаба, сессии 7–8 | TLS-секрет, `IngressRoute` с TLS, обзор cert-manager | желательно |
| TCP/UDP-роутеры, метрики Prometheus, журнал JSON | Traefik-лаба, сессии 9–10 | `IngressRouteTCP`, наблюдаемость (11) | по желанию |

**Что берётся готовым: `starter/` из шага 10.5 Traefik-лабы** (`~/traefik-lab/starter`, в репозиторий не кладётся — решение владельца 13.10):

- `coffeeshop/api` — Node.js API с `/health`, `/menu`, `/orders` (с `Idempotency-Key`), `/info`, `/slow`, `/flaky`, `/drop`; образ собирается как `coffeeshop-api:v1` (**вместо** прежнего `traefik-lab-api:v1`);
- `coffeeshop/web`, `coffeeshop/db/init.sql` (PostgreSQL 18), Adminer — те же сервисы, имена `db`, `api`, `web`, `adminer`;
- `edge/` — метки Traefik как **образец для перевода** в манифесты (`rule`, `middlewares`, `healthcheck`, `loadbalancer.server.port`);
- `smoke.sh` — **приёмочный тест**: сессии Kubernetes-лабы доказывают, что стек в кластере отвечает так же, как в Compose (адреса `shop.localhost`, `adminer.shop.localhost`, `/api` без префикса, две копии API, пароль админки, HTTPS);
- `monitoring/` — Prometheus и Grafana: в Kubernetes ставятся через Helm (сессия 11).

**Что переносится из Traefik-лабы в Kubernetes (ориентир для написания, точный состав — по мере работы):**

| Traefik-лаба | Kubernetes-лаба |
|---|---|
| метки роутера (3.2–3.5) | `Ingress` и `IngressRoute` (5.5) |
| middlewares: `stripPrefix`, `headers`, `basicAuth`, `chain` (4.x) | `Middleware` (CRD Traefik) (5.6) |
| `rateLimit`, `retry`, `circuitBreaker` (5.x) | `Middleware`; ограничения на уровне кластера — `NetworkPolicy`, `ResourceQuota` (9) |
| реплики, healthcheck (6.1–6.2) | `Deployment` (`replicas`), `readiness`/`liveness` probes (4, 6) |
| canary и blue/green (6.4, 6.6) | rolling update и rollback (4), веса `TraefikService` (12) |
| mkcert, mTLS, ACME (7, 8) | TLS-секрет, `TLSOption`, обзор cert-manager (5, 9) |
| TCP и UDP-роутеры (9.2–9.3) | `IngressRouteTCP`, `IngressRouteUDP` (необязательно) |
| метрики, журнал, дерево вопросов (10.1–10.4) | Prometheus через Helm, `kubectl logs`, дерево вопросов для Pod и Service (11) |
| `up.sh`, `smoke.sh`, Production Hell (10.5–10.6) | итоговый Helm chart с `helm test` и свой Production Hell (13) |

**Что не требуется:** проходить Traefik-лабу целиком, знать ACME и плагины; всё, что нужно, повторяется на новом материале. **Что обязательно поставить отдельно:** `kind`, `kubectl`, `helm` (в Docker- и Traefik-лабах их не было).

**Ворота очерёдности выполнены:** лаба N+1 не пишется целиком, пока у N нет проверенного `starter/` — у Traefik он собран и проверен (18.10.2026: поднят с чистого стенда, `smoke.sh` — «всё в порядке»). Версии на момент написания перепроверить: Helm, Traefik chart, судьба `ingress-nginx`, Calico/Cilium в kind.

**Откуда темы исходного списка:** разд. 1 → сессия 1; 2 → 2; 3 → 3; 4 → 4; 5 → 5; 6 → 6; 7 → 7; 8 → 8; 9 → 10; 10 → 11; 11–12 → 12; 13 → 13. От себя добавлено (нужно для эксплуатации): сессия 9 «Безопасность» и `kustomize` в 13.

### Сессия 1 · Азбука и окружение (~4 ч)
**Слова:** контейнер, оркестратор, кластер, узел, манифест, YAML, `kubectl`, `kind`, контекст, `kubeconfig`.
- 1.1 Проблема: что делать, когда контейнеров сотни (самолечение, масштабирование, обновления)
- 1.2 Что такое Kubernetes и Helm и какие задачи решают; чем отличаются от Compose и Swarm
- 1.3 Минимум Docker и Compose для режима «с нуля»; проверка стартового состояния для режима «продолжение»
- 1.4 Инструменты: `kubectl`, `kind`, `helm` (macOS/Linux/Windows — **как ещё**), автодополнение, редактор (VS Code и плагин YAML)
- 1.5 Локальный кластер: `kind create cluster`, конфиг-файл (`extraPortMappings`), `kubectl cluster-info`, контексты и `kubeconfig`
- 1.6 YAML с нуля и структура манифеста (`apiVersion`, `kind`, `metadata`, `spec`); `kubectl explain`
- 1.7 Организация каталога проекта
- 🔨 `connection refused` на `kubectl`: кластер не запущен/не тот контекст
- **Приёмка:** кластер из 1 control-plane и 2 worker-узлов, `kubectl get nodes` готов

### Сессия 2 · Архитектура и объекты (~4 ч)
**Слова:** control plane, `kube-apiserver`, `etcd`, scheduler, controller manager, `kubelet`, `kube-proxy`, объект, желаемое/текущее состояние, reconcile.
- 2.1 Компоненты кластера и как они общаются (путь `kubectl apply` до запущенного контейнера)
- 2.2 Модель «желаемое состояние → контроллеры → реальность»
- 2.3 Императивный и декларативный подходы: `kubectl run/create` vs `apply -f`
- 2.4 Что такое объект: `metadata`, labels, selectors, annotations, `ownerReferences`
- 2.5 API: группы, версии, `kubectl api-resources`, `api-versions`
- 2.6 Первые команды: `get`, `describe`, `delete`, `apply`, `diff`, `-o yaml/wide/json`, `jsonpath`
- 🔨 «apply ничего не делает»: опечатка в `kind`
- **Приёмка:** могу описать путь `apply` по компонентам и показать в `kube-system` каждый из них

### Сессия 3 · Pod и Service (~4 ч)
**Слова:** Pod, контейнер в Pod, фаза, `restartPolicy`, Service, `ClusterIP`, endpoint, `port-forward`.
- 3.1 Pod: что это (аналогия: «общая квартира» контейнеров), манифест, запуск
- 3.2 Жизненный цикл Pod: `Pending → Running → Succeeded/Failed`, причины статусов
- 3.3 `logs`, `exec`, `describe`, события; несколько контейнеров в Pod
- 3.4 Service: зачем (Pod’ы смертны), selector, `port`/`targetPort`
- 3.5 Доступ: `port-forward`, DNS внутри кластера (`svc.namespace.svc.cluster.local`)
- 3.6 Образ API в kind (`kind load docker-image`), `imagePullPolicy`
- 🔨 `ImagePullBackOff` / `ErrImageNeverPull`
- **Приёмка:** API в Pod, доступен через Service и `port-forward`

### Сессия 4 · Deployment и обновления (~4 ч)
**Слова:** ReplicaSet, Deployment, реплика, стратегия, rolling update, `maxSurge`, `maxUnavailable`, rollout, откат.
- 4.1 Зачем Deployment и как связаны Deployment → ReplicaSet → Pod; самолечение (убить Pod)
- 4.2 Реплики и масштабирование `scale`
- 4.3 Обновление образа и rolling update: `maxSurge`/`maxUnavailable`, `minReadySeconds`
- 4.4 `rollout status/history/undo/pause/resume`, ревизии
- 4.5 Проверка состояния приложения, `kubectl wait`
- 4.6 Стратегия `Recreate` и когда она нужна
- 🔨 обновление на «битый» образ — Deployment застрял; откат
- **Приёмка:** обновление без простоя, откат одной командой

### Сессия 5 · Сети и Ingress (~4 ч)
**Слова:** CNI, ClusterIP, NodePort, LoadBalancer, DNS (`CoreDNS`), Ingress, IngressRoute, Ingress Controller.
- 5.1 Сетевая модель: у каждого Pod свой IP; Pod ↔ Pod без NAT
- 5.2 Типы Service: `ClusterIP`, `NodePort`, `LoadBalancer` (в kind), `headless`
- 5.3 DNS кластера: как резолвится имя, `nslookup` из Pod
- 5.4 Зачем Ingress; Ingress Controller; **Traefik в кластере** (установка, `IngressClass`)
- 5.5 Ресурс `Ingress` и `IngressRoute` (CRD Traefik): маршрутизация по `Host` и пути
- 5.6 kind и порты: `extraPortMappings`, как открыть приложение с Mac
- 🔨 Ingress есть, а 404/503: `Service`, `endpoints`, селектор
- **Приёмка:** `http://shop.localhost` открывает frontend, `/api` — API

### Сессия 6 · Хранение данных (~4 ч)
**Слова:** Volume, `emptyDir`, PersistentVolume, PersistentVolumeClaim, StorageClass, провижининг, `accessModes`, StatefulSet.
- 6.1 Временные и постоянные данные; `emptyDir`, `hostPath` (риски)
- 6.2 PV, PVC, StorageClass: кто за что отвечает; динамический провижининг в kind
- 6.3 PostgreSQL 18 в кластере: том в `/var/lib/postgresql`, переменные окружения
- 6.4 Подключение PVC к Deployment; проверка: Pod пересоздан — данные на месте
- 6.5 StatefulSet: стабильные имена и тома, зачем для БД; `volumeClaimTemplates`
- 6.6 Резервная копия БД (`pg_dump` через `kubectl exec`) и `CronJob` (обзор)
- 🔨 PVC в `Pending`: нет StorageClass / неверный `accessMode`
- **Приёмка:** данные БД переживают удаление Pod

### Сессия 7 · Секреты и конфигурация (~4 ч)
**Слова:** ConfigMap, Secret, base64 (≠ шифрование), переменная окружения, монтирование файла, `envFrom`.
- 7.1 Зачем отделять конфиг от образа (12-factor)
- 7.2 ConfigMap: из литералов и файлов; как подключить (env, том, `subPath`); обновление и когда оно видно
- 7.3 Secret: типы (`Opaque`, `dockerconfigjson`, `tls`), создание, подключение
- 7.4 Безопасность секретов: base64 — не защита; RBAC на секреты; шифрование etcd (обзор)
- 7.5 Несколько взаимосвязанных сервисов: API ↔ БД ↔ Adminer
- 7.6 Отладка конфигураций и Ingress: типовые ошибки
- 🔨 `CreateContainerConfigError`: нет ключа в Secret
- **Приёмка:** пароль БД лежит в Secret, конфиг API — в ConfigMap

### Сессия 8 · Эксплуатация и диагностика (~4 ч)
**Слова:** namespace, квота, `LimitRange`, probe (`liveness/readiness/startup`), `initContainer`, Job, CronJob, события, Dashboard.
- 8.1 Namespace: `dev`/`prod`, переключение контекста, `ResourceQuota`, `LimitRange`
- 8.2 Probes: `readiness`, `liveness`, `startup`; чем отличаются; crash-тест
- 8.3 `requests` и `limits`, `OOMKilled`, QoS-классы
- 8.4 `initContainer` (ждать БД), Job, CronJob
- 8.5 Dashboard и `k9s`: как смотреть состояние
- 8.6 Диагностика: таблица «статус → причина» (`Pending`, `CrashLoopBackOff`, `ImagePullBackOff`, `OOMKilled`, `Evicted`), `describe`, `events`, `logs --previous`, `kubectl debug`
- 🔨 **Production Hell 1:** 5 поломок в стеке
- **Приёмка:** по каждой поломке нахожу причину по статусу и событиям

### Сессия 9 · Безопасность и сеть-политики (~4 ч)
**Слова:** RBAC, `Role`, `RoleBinding`, `ServiceAccount`, `NetworkPolicy`, `securityContext`, Pod Security Standards.
- 9.1 RBAC: `Role`/`ClusterRole`, `Binding`, `kubectl auth can-i`, `--as`
- 9.2 `ServiceAccount` и токены; доступ Pod к API кластера
- 9.3 `securityContext`: non-root, `readOnlyRootFilesystem`, `capabilities`
- 9.4 Pod Security Standards (`restricted`) на namespace
- 9.5 `NetworkPolicy`: «запретить всё» + разрешить нужное (требует CNI с поддержкой политик — в kind **по умолчанию CNI их не применяет**: показать это и как включить Calico/Cilium, **сверьтесь**)
- 9.6 Образы и цепочка поставки (обзор): подпись, сканирование
- 🔨 политика есть, но не работает (CNI)
- **Приёмка:** frontend не достучался до БД, API — достучался; проверено `curl` из Pod

### Сессия 10 · Helm, основы (~4 ч)
**Слова:** chart, release, repository, `values`, шаблон, `Chart.yaml`, `helm install/upgrade`.
- 10.1 Зачем Helm: «менеджер пакетов + шаблонизатор + учёт релизов»
- 10.2 Установка и архитектура Helm (без Tiller — почему)
- 10.3 Готовые charts: `helm search hub/repo`, `helm show values`, установка и удаление
- 10.4 `helm create`: структура chart (`Chart.yaml`, `values.yaml`, `templates/`, `charts/`)
- 10.5 Перенос Deployment+Service API в chart, `helm template` и `lint`
- 10.6 `install`, `upgrade --set`, `get values/manifest`
- 🔨 `helm install` падает: неверный YAML после шаблонизации
- **Приёмка:** API устанавливается и обновляется chart’ом

### Сессия 11 · Шаблоны Helm (~4 ч)
**Слова:** Go template, контекст (`.`), `.Values`, `.Release`, pipeline, функция, `define`, `include`, `range`, `with`.
- 11.1 Синтаксис `{{ }}`, пробелы `{{-`, встроенные объекты
- 11.2 Функции и pipelines: `default`, `quote`, `upper`, `toYaml | nindent`, `required`
- 11.3 `if/else`, `with`, `range` по спискам и словарям, `tuple`
- 11.4 `define`/`template`/`include` и `_helpers.tpl`: общие labels одним блоком
- 11.5 Шаблоны для приложения и API; включаемые ресурсы (Ingress по флагу)
- 11.6 Chart для PostgreSQL (StatefulSet + PVC + Secret)
- 11.7 Оптимизация структуры chart’а, subcharts и зависимости
- 🔨 неверный `nindent` — валидный шаблон, невалидный YAML
- **Приёмка:** CoffeeShop (API + БД) ставится двумя chart’ами

### Сессия 12 · Репозитории, релизы, окружения (~4 ч)
**Слова:** репозиторий charts, `index.yaml`, релиз, ревизия, `rollback`, `--atomic`, `values-dev.yaml`.
- 12.1 Структура репозитория, `helm package`, `helm repo index`, раздача (локально или статическим хостингом; без секретов)
- 12.2 `repo add/update/search`, установка из своего репозитория
- 12.3 Жизненный цикл: `upgrade --install`, `history`, `rollback`, `uninstall`, `--atomic`, `--wait`
- 12.4 Проверки: `lint`, `template`, `--dry-run --debug`, `helm test`, `helm diff` (плагин)
- 12.5 Окружения: `values-dev/staging/prod.yaml`, `-f`, `--set`, приоритет
- 12.6 Секреты в Helm: `helm-secrets`/Sealed Secrets; ничего чувствительного в `values.yaml` репозитория
- 🔨 релиз застрял в `pending-upgrade`
- **Приёмка:** chart из своего репозитория ставится в dev и prod с разными значениями

### Сессия 13 · Итоговый проект (~4 ч)
**Слова:** umbrella chart, GitOps (обзор), `kustomize`, `overlay`.
- 13.1 Подготовка чистого кластера и образов
- 13.2 Umbrella-chart CoffeeShop: API, frontend, PostgreSQL, Ingress, ConfigMap/Secret
- 13.3 `values-prod.yaml`: ресурсы, реплики, probes, NetworkPolicy, securityContext
- 13.4 Установка, обновление, откат, проверка работоспособности
- 13.5 Сравнение: тот же стек через `kustomize` (`base` + `overlays`); Helm vs Kustomize
- 13.6 «Что дальше»: GitOps (Argo CD/Flux), операторы, Gateway API (обзор)
- 🔨 **Production Hell 2** без подсказок: релиз с 5 поломками
- **Приёмка:** `helm install coffee ./chart -f values-prod.yaml` на чистом kind-кластере даёт рабочий сайт; `upgrade` и `rollback` проверены

**Справка:** симптом → причина → что делать (`ImagePullBackOff`, `CrashLoopBackOff`, `Pending`, `OOMKilled`, `CreateContainerConfigError`, `x509`, `forbidden`…), команды с разбором, порты и процессы, глоссарий, 60 вопросов для собеседования, «что дальше».

## Решения владельца (11.10.2026)
1. Helm остаётся внутри `kubernetes.html` (13 сессий) — принято (рекомендация плана).
2. Безопасность (сессия 9) и `kustomize` — оставляем.
3. **Calico в kind для `NetworkPolicy` — ставим** (версия и способ — сверить при написании).

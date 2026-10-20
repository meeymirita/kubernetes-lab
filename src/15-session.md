# Сессия 15 · Итоговый проект
dur: ~4 ч

## 15.1 Чистый кластер и образы | short: Чистый старт | est: ~30 мин
### intro
**Слова шага:** *чистый стенд*, *`kind delete cluster`*, *`kind load docker-image`*, *воспроизводимость*.

:::tip Если совсем просто
Проверка, что твой рецепт действительно работает, — это приготовить по нему на чужой кухне, а не на своей, где всё уже разложено. Поэтому сначала сносим кластер, поднимаем новый — и дальше всё делаем только по chart’у и командам из этой сессии, без «я там руками когда-то поправила».
:::

```svg
@umbrella-house
```

```bash run
cd ~/kubernetes-lab
kind delete cluster --name coffeeshop
kind create cluster --config kind-config.yaml --image kindest/node:v1.37.0
kubectl get nodes
docker image inspect coffeeshop-api:v1 --format '{{.Id}}' | cut -c1-19
kind load docker-image coffeeshop-api:v1 --name coffeeshop
helm repo add traefik https://traefik.github.io/charts && helm repo update
helm install traefik traefik/traefik --namespace traefik --create-namespace \
  --set ports.web.hostPort=80 --set ports.websecure.hostPort=443 \
  --set hostNetwork=true --set service.type=ClusterIP --wait --timeout 3m
kubectl get pods -n traefik
```

### result
```out auto
```

Что нужно «снаружи» чистого кластера: образ `coffeeshop-api:v1` (собранный в шаге 1.3 из `starter/`) загружен в узлы `kind` (шаг 3.6), и Ingress Controller Traefik стоит (шаг 5.4). Всё остальное — CoffeeShop целиком — будет выкатываться одной командой.

### why
Если проект поднимается только на «обжитом» кластере, то это не проект, а набор воспоминаний. Чистый старт выявляет всё, о чём мы забыли записать: namespace, образ, Ingress Controller. Эти внешние предпосылки фиксируем в README проекта.

### deep Если не получилось
- **Порт 80 занят** — остановили ли вы старые стенды предыдущих лаб (`docker ps`)?
- **`docker image inspect` не находит образ** — пересобери его из `starter/` (шаг 1.3) и повтори `kind load`.

### quiz
- Зачем начинать итоговый проект с удаления кластера?
- Что должно быть в кластере до установки chart’а CoffeeShop?

### links
- https://kind.sigs.k8s.io/docs/user/quick-start/#loading-an-image-into-your-cluster | загрузка образов в kind | kind: Loading an Image

## 15.2 Umbrella chart CoffeeShop | short: Umbrella chart | est: ~60 мин
### intro
**Слова шага:** *umbrella chart*, *`global`*, *`fullnameOverride`*, *`condition`*, *subcharts API, web, БД*.

:::tip Если совсем просто
Дом (umbrella) с тремя квартирами: API, веб-сайт, база. У каждой квартиры своя планировка (subchart), у дома — общие правила (`global`): общий домен, общий пароль к базе и так далее. Въезд один — `helm install coffee ./coffeeshop`.
:::

Исправим две вещи, о которых говорили раньше: имена объектов (чтобы база называлась `db`, а не `coffee-db`) и общий пароль. Для этого в обоих chart’ах добавляем поддержку `fullnameOverride` и `global.dbPassword`, а третий chart — веб-сайт — делаем новым.

```bash run
cd ~/kubernetes-lab/charts
# 1. fullname: можно задать явно
python3 - <<'PY'
import re
p = 'coffeeshop-api/templates/_helpers.tpl'
s = open(p).read()
s = s.replace('{{- printf "%s-api" .Release.Name | trunc 63 | trimSuffix "-" -}}',
              '{{- default (printf "%s-api" .Release.Name) .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}')
open(p, 'w').write(s)
p = 'coffeeshop-api/values.yaml'
s = open(p).read()
s = 'fullnameOverride: ""\n' + s
s = s.replace('  password: ""          # обязательный: задаётся при установке, не хранится здесь',
              '  password: ""          # обязательный: задаётся при установке, не хранится здесь\n  existingSecret: ""')
open(p, 'w').write(s)
PY
# 2. пароль БД берётся из global, если не задан локально
cat > coffeeshop-api/templates/secret.yaml <<'EOF'
apiVersion: v1
kind: Secret
metadata:
  name: {{ include "coffeeshop-api.fullname" . }}
  labels:
    {{- include "coffeeshop-api.labels" . | nindent 4 }}
type: Opaque
stringData:
  DB_PASSWORD: {{ required "задай global.dbPassword или db.password" (default .Values.global.dbPassword .Values.db.password) | quote }}
EOF
cat > coffeeshop-db/templates/secret.yaml <<'EOF'
apiVersion: v1
kind: Secret
metadata:
  name: {{ .Release.Name }}-auth
type: Opaque
stringData:
  POSTGRES_USER: {{ .Values.auth.user | quote }}
  POSTGRES_DB: {{ .Values.auth.database | quote }}
  POSTGRES_PASSWORD: {{ required "задай global.dbPassword или auth.password" (default .Values.global.dbPassword .Values.auth.password) | quote }}
EOF
grep -n 'required' coffeeshop-api/templates/secret.yaml coffeeshop-db/templates/secret.yaml
```

### result
```out auto
```

(Секция `global` в subchart’е может отсутствовать при отдельной установке — тогда `.Values.global.dbPassword` пуст, и `required` честно сообщит об этом. Чтобы шаблон не падал на отсутствующем `global`, добавим в оба `values.yaml` `global: {}`.)

Веб-chart (nginx, отдающий статику frontend’а из `starter/`) — по образцу API, короче, с собственным Service и Ingress на `/`:

```bash run
cd ~/kubernetes-lab/charts
printf 'global: {}\n' | cat - coffeeshop-api/values.yaml > /tmp/v && mv /tmp/v coffeeshop-api/values.yaml
printf 'global: {}\n' | cat - coffeeshop-db/values.yaml  > /tmp/v && mv /tmp/v coffeeshop-db/values.yaml
helm create coffeeshop-web >/dev/null && rm -rf coffeeshop-web/templates/* && : > coffeeshop-web/values.yaml
cat > coffeeshop-web/Chart.yaml <<'EOF'
apiVersion: v2
name: coffeeshop-web
description: Фронтенд CoffeeShop (nginx)
type: application
version: 0.1.0
appVersion: "v1"
EOF
cat > coffeeshop-web/values.yaml <<'EOF'
global: {}
fullnameOverride: ""
replicaCount: 1
image: {repository: coffeeshop-web, tag: v1}
service: {port: 80}
resources:
  requests: {cpu: 20m, memory: 32Mi}
  limits: {memory: 64Mi}
ingress:
  enabled: true
  host: shop.localhost
  className: traefik
EOF
cat > coffeeshop-web/templates/web.yaml <<'EOF'
{{- $name := default (printf "%s-web" .Release.Name) .Values.fullnameOverride }}
apiVersion: apps/v1
kind: Deployment
metadata: {name: {{ $name }}}
spec:
  replicas: {{ .Values.replicaCount }}
  selector: {matchLabels: {app: {{ $name }}}}
  template:
    metadata: {labels: {app: {{ $name }}}}
    spec:
      containers:
        - name: web
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          ports: [{containerPort: 80}]
          readinessProbe: {httpGet: {path: /, port: 80}}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
---
apiVersion: v1
kind: Service
metadata: {name: {{ $name }}}
spec:
  selector: {app: {{ $name }}}
  ports: [{port: {{ .Values.service.port }}, targetPort: 80}]
{{- if .Values.ingress.enabled }}
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata: {name: {{ $name }}}
spec:
  ingressClassName: {{ .Values.ingress.className }}
  rules:
    - host: {{ .Values.ingress.host | quote }}
      http:
        paths:
          - {path: /, pathType: Prefix, backend: {service: {name: {{ $name }}, port: {number: {{ .Values.service.port }}}}}}
{{- end }}
EOF
helm lint coffeeshop-web
```

### result
```out auto
```

Образ `coffeeshop-web:v1` — frontend из `starter/` (тот же nginx со статикой, что мы запускали в шаге 5.5; если он у тебя назывался иначе, поправь `image.repository`). Теперь соберём сам umbrella:

```bash run
cd ~/kubernetes-lab/charts
rm -rf coffeeshop && mkdir coffeeshop && cd coffeeshop
cat > Chart.yaml <<'EOF'
apiVersion: v2
name: coffeeshop
description: Весь CoffeeShop одним релизом
type: application
version: 1.0.0
appVersion: "v1"
dependencies:
  - {name: coffeeshop-db,  version: 0.1.0, repository: "file://../coffeeshop-db"}
  - {name: coffeeshop-api, version: 0.1.0, repository: "file://../coffeeshop-api"}
  - {name: coffeeshop-web, version: 0.1.0, repository: "file://../coffeeshop-web"}
EOF
cat > values.yaml <<'EOF'
global:
  dbPassword: ""     # задаётся при установке

coffeeshop-db:
  fullnameOverride: db
coffeeshop-api:
  fullnameOverride: coffeeshop-api
  db: {host: db}
  ingress: {enabled: true, host: shop.localhost}
coffeeshop-web:
  fullnameOverride: coffeeshop-web
EOF
helm dependency update
helm lint . --set global.dbPassword=x
helm template coffee . --set global.dbPassword=x | grep -E '^kind: (Deployment|StatefulSet|Service|Ingress|Secret)$' | sort | uniq -c
```

### result
```out auto
```

Чтобы у базы было фиксированное имя `db`, chart БД тоже должен понимать `fullnameOverride`: он пока берёт имя от `.Release.Name`. Поправим его (имя Service, StatefulSet и Secret теперь строится из одной переменной):

```bash run
cd ~/kubernetes-lab/charts
sed -i.bak 's|{{ .Release.Name }}|{{ default .Release.Name .Values.fullnameOverride }}|g' coffeeshop-db/templates/service.yaml coffeeshop-db/templates/statefulset.yaml coffeeshop-db/templates/secret.yaml
rm -f coffeeshop-db/templates/*.bak
printf 'fullnameOverride: ""\n' >> coffeeshop-db/values.yaml
cd coffeeshop && helm dependency update >/dev/null
helm template coffee . --set global.dbPassword=x | grep -E '^  name: (db|coffee)' | sort | uniq -c
```

### result
```out auto
```

Теперь у базы имя `db`. Пароль задаётся **один раз** через `global.dbPassword` и попадает и в API, и в БД.

### why
Один набор имён, один пароль, одна команда установки — и ровно по этой причине в проектах делают umbrella: приложение из трёх частей — всё равно одно приложение. Остаётся возможность ставить части по отдельности, если нужно (`helm install db charts/coffeeshop-db`).

### deep Если не получилось
- **Имя объекта не `db`, а `coffee`** — `sed` не заменил имя в одном из файлов chart’а БД; проверь `grep -rn 'Release.Name' coffeeshop-db/templates`.
- **`helm dependency update` не находит `../coffeeshop-web`** — проверь, что `coffeeshop-web` создан в `~/kubernetes-lab/charts/`.

### quiz
- Как передать один пароль сразу двум subchart’ам?
- Для чего в subchart’ах `fullnameOverride`?
- Когда umbrella-подход удобнее набора отдельных релизов?

### links
- https://helm.sh/docs/chart_template_guide/subcharts_and_globals/#global-chart-values | global values | Helm: Global Chart Values
- https://helm.sh/docs/howto/charts_tips_and_tricks/ | советы по chart’ам | Helm: Tips and Tricks

## 15.3 values-prod: ресурсы, реплики, пробы, политики | short: values-prod | est: ~45 мин
### intro
**Слова шага:** *боевые значения*, *`securityContext`*, *`NetworkPolicy` в chart’е*, *осмысленные пробы*.

:::tip Если совсем просто
В «учебной» версии мы позволяли себе шутки — один Pod, пароль в виде `s3cret`, никаких запретов. В боевой версии то же приложение приходит с ремнями безопасности: несколько реплик, ограничения контейнера, закрытая база. Всё это — не новый код, а другие значения (и пара новых шаблонов).
:::

Добавим два новых шаблона в `coffeeshop-api` — `securityContext` и `NetworkPolicy` для БД (по флагам) — и боевой файл значений:

```bash run
cd ~/kubernetes-lab/charts
python3 - <<'PY'
p = 'coffeeshop-api/templates/deployment.yaml'
s = open(p).read()
s = s.replace("""    spec:
      containers:
        - name: api
""", """    spec:
      {{- with .Values.podSecurityContext }}
      securityContext:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      containers:
        - name: api
          {{- with .Values.containerSecurityContext }}
          securityContext:
            {{- toYaml . | nindent 12 }}
          {{- end }}
""", 1)
open(p, 'w').write(s)
p = 'coffeeshop-api/values.yaml'
s = open(p).read()
s += """podSecurityContext: {}
containerSecurityContext: {}
"""
open(p, 'w').write(s)
PY
cat > coffeeshop-db/templates/networkpolicy.yaml <<'EOF'
{{- if .Values.networkPolicy.enabled }}
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ default .Release.Name .Values.fullnameOverride }}-only-api
spec:
  podSelector:
    matchLabels:
      app: {{ default .Release.Name .Values.fullnameOverride }}
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels: {{- toYaml .Values.networkPolicy.allowFrom | nindent 14 }}
      ports: [{port: 5432}]
{{- end }}
EOF
printf 'networkPolicy:\n  enabled: false\n  allowFrom: {app.kubernetes.io/name: coffeeshop-api}\n' >> coffeeshop-db/values.yaml
cd coffeeshop
cat > values-prod.yaml <<'EOF'
coffeeshop-db:
  networkPolicy: {enabled: true, allowFrom: {app.kubernetes.io/name: coffeeshop-api}}
  storage: {size: 2Gi}
coffeeshop-api:
  replicaCount: 3
  resources:
    requests: {cpu: 100m, memory: 128Mi}
    limits: {memory: 256Mi}
  podSecurityContext:
    runAsNonRoot: true
    seccompProfile: {type: RuntimeDefault}
  containerSecurityContext:
    allowPrivilegeEscalation: false
    capabilities: {drop: ["ALL"]}
coffeeshop-web:
  replicaCount: 2
EOF
helm dependency update >/dev/null
helm lint . -f values-prod.yaml --set global.dbPassword=x
helm template coffee . -f values-prod.yaml --set global.dbPassword=x | grep -E 'kind: NetworkPolicy|replicas: 3|allowPrivilegeEscalation'
```

### result
```out auto
```

Заметь: `NetworkPolicy` создаётся только если включена **значением** (в `values-prod.yaml`), поэтому в `dev` без него всё остаётся простым. Метка в `allowFrom` должна совпадать с меткой Pod API — в нашем шаблоне это `app.kubernetes.io/name: coffeeshop-api` (из `selectorLabels`, шаг 13.4). Ровно здесь и спотыкаются на практике: политика написана, метка не та, и либо API не пускает к базе, либо (как в шаге 9.7) политика ничего не выбирает. Всегда проверяй `wget`/`psql` из Pod’а API.

### why
Различия `dev` и `prod` — только в одном файле значений, и они все видны одновременно в диффе. Именно так выглядит «боевая готовность» в Kubernetes: не отдельный код, а набор ограничений и запасов.

### deep Если не получилось
- **API не стартует с `runAsNonRoot`** — шаг 9.3: проверь, под каким пользователем собран образ; при необходимости добавь `runAsUser`.

### quiz
- Какие свойства делают конфигурацию «боевой», а не учебной?
- Почему `NetworkPolicy` включена флагом, а не безусловно?

### links
- https://kubernetes.io/docs/concepts/security/pod-security-standards/#restricted | restricted | Kubernetes: Restricted profile

## 15.4 Установка, обновление, откат, проверка | short: Весь цикл | est: ~45 мин
### intro
**Слова шага:** *`helm install`*, *`upgrade`*, *`rollback`*, *дымовой тест*.

:::tip Если совсем просто
Прогоняем весь жизненный цикл: поставили, проверили, обновили, сломали (на всякий случай), откатили. Если все пять действий проходят — релиз «боевой».
:::

```bash run
cd ~/kubernetes-lab/charts/coffeeshop
helm upgrade --install coffee . -n coffee --create-namespace -f values-prod.yaml --set global.dbPassword=s3cret --atomic --wait --timeout 6m
kubectl get pods,svc,ingress,pvc -n coffee
for u in http://shop.localhost/ http://shop.localhost/api/health; do curl -s -o /dev/null -w "$u: HTTP %{http_code}\n" $u; done
helm history coffee -n coffee
```

### result
```out auto
```

Обновление (новая версия приложения → меняем `image.tag`) и откат:

```bash run
cd ~/kubernetes-lab/charts/coffeeshop
docker tag coffeeshop-api:v1 coffeeshop-api:v2
kind load docker-image coffeeshop-api:v2 --name coffeeshop
helm upgrade coffee . -n coffee -f values-prod.yaml --set global.dbPassword=s3cret --set coffeeshop-api.image.tag=v2 --atomic --wait --timeout 6m
kubectl get deploy coffeeshop-api -n coffee -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
helm upgrade coffee . -n coffee -f values-prod.yaml --set global.dbPassword=s3cret --set coffeeshop-api.image.tag=v3-broken --atomic --wait --timeout 90s 2>&1 | tail -2
helm history coffee -n coffee
helm rollback coffee 2 -n coffee --wait
kubectl get deploy coffeeshop-api -n coffee -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
curl -s -o /dev/null -w "после отката: HTTP %{http_code}\n" http://shop.localhost/api/health
```

### result
```out auto
```

**Приёмка сессии:** `helm install` на чистом кластере поднимает рабочий сайт (`shop.localhost`, `/api/health` отвечают `200`); `upgrade` на `v2` проходит, `upgrade` на заведомо плохой тег откатывается `--atomic`, ручной `rollback` возвращает рабочую версию. Данные БД при всех этих манёврах остались на месте (проверь: `kubectl exec -n coffee statefulset/db -- psql -U coffeeshop -c '\dt'`).

### why
Если все пять действий отработали на чистом кластере без ручных правок, то в этом и есть смысл «воспроизводимости»: так же будет работать на любом другом кластере, куда доедет тот же chart.

### deep Если не получилось
- **`/api/health` отвечает `404` или `503`** — проход по диагностике из шага 8.6: Pod → Service → Ingress; пароль БД не совпал — Pod API в `CrashLoopBackOff`.
- **Первый `install` по `--atomic` откатился** — читай `kubectl get events -n coffee --sort-by=.lastTimestamp`, пока не удалил namespace.

### quiz
- Как проверить, что `rollback` вернул именно прежнее приложение?
- Что защищает данные БД при откате приложения?

### links
- https://helm.sh/docs/helm/helm_upgrade/ | helm upgrade | Helm: helm upgrade

## 15.5 Тот же стек через Kustomize | short: Kustomize | est: ~40 мин
### intro
**Слова шага:** *`kustomize`*, *`base`*, *`overlay`*, *`kubectl apply -k`*, *patch*.

:::tip Если совсем просто
Helm — рецепт с пустыми окошками. Kustomize — готовый, никогда не изменяемый рецепт плюс «листочки-поправки»: «в этом ресторане берём вдвое больше реплик». Никаких шаблонов `{{ }}`: файл всегда обычный валидный YAML, а различия накладываются поверх.
:::

Kustomize встроен в `kubectl` (`kubectl apply -k`, `kubectl kustomize`). Сделаем `base` из одного Deployment и два оверлея:

```bash run
cd ~/kubernetes-lab && rm -rf kustomize-demo && mkdir -p kustomize-demo/base kustomize-demo/overlays/dev kustomize-demo/overlays/prod && cd kustomize-demo
cat > base/web.yaml <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata: {name: web}
spec:
  replicas: 1
  selector: {matchLabels: {app: web}}
  template:
    metadata: {labels: {app: web}}
    spec:
      containers:
        - {name: web, image: nginx:alpine, resources: {requests: {cpu: 20m, memory: 32Mi}}}
EOF
cat > base/kustomization.yaml <<'EOF'
resources: [web.yaml]
EOF
cat > overlays/dev/kustomization.yaml <<'EOF'
resources: [../../base]
namePrefix: dev-
EOF
cat > overlays/prod/kustomization.yaml <<'EOF'
resources: [../../base]
namePrefix: prod-
replicas:
  - {name: web, count: 3}
images:
  - {name: nginx, newTag: 1.30-alpine}
patches:
  - target: {kind: Deployment, name: web}
    patch: |-
      - op: add
        path: /spec/template/spec/containers/0/resources/limits
        value: {memory: 64Mi}
EOF
echo "=== dev:";  kubectl kustomize overlays/dev  | grep -E 'name:|replicas:|image:'
echo "=== prod:"; kubectl kustomize overlays/prod | grep -E 'name:|replicas:|image:|memory'
```

### result
```out auto
```

| | Helm | Kustomize |
|---|---|---|
| Идея | шаблоны + значения | готовый YAML + накладываемые правки |
| Читаемость | `{{ }}` внутри YAML | чистый YAML |
| Упаковка и версии, репозитории | да | нет (обычно Git-репозиторий) |
| Учёт релизов, откат | да (`history`, `rollback`) | нет (откат — это Git и `apply`) |
| Гибкость логики (`if`, `range`) | высокая | ограниченная (заплатки) |
| Ставить чужие приложения | основной способ | редко |
| Типичный выбор | чужие приложения, сложные параметры | свои приложения с 2–3 окружениями; GitOps |

Правило большого пальца: **чужие** приложения — Helm; **свои** — любой из двух, на вкус команды; их часто сочетают (Helm для чужого, Kustomize для своих окружений поверх; в GitOps-инструментах оба поддерживаются нативно).

### why
Знать оба важно потому, что на любом реальном проекте ты встретишь и тот, и другой. Kustomize не нужно «учить» — он умещается в три файла; понимание «чем отличается» — вот что даёт выбор.

### deep Если не получилось
- **`kubectl kustomize` не знает `replicas:`** — слишком старый `kubectl`; проверь `kubectl version --client`.

### quiz
- Чем Kustomize отличается от Helm по подходу к различиям окружений?
- Что есть у Helm, чего нет у Kustomize?
- Когда разумно использовать их вместе?

### links
- https://kubectl.docs.kubernetes.io/references/kustomize/ | справочник Kustomize | Kubernetes SIG: Kustomize reference
- https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/ | Kustomize в документации | Kubernetes: Declarative Management with Kustomize

## 15.6 Что дальше: GitOps, операторы, Gateway API | short: Что дальше | est: ~30 мин
### intro
**Слова шага:** *GitOps*, *Argo CD*, *Flux*, *оператор*, *Gateway API*.

:::tip Если совсем просто
До сих пор выкатывала ты — руками, командой. В GitOps выкатывает робот: он смотрит в Git-репозиторий, где лежит желаемое состояние, и сам приводит кластер в соответствие (ровно та же идея reconcile, что в шаге 2.2, только «желаемое» живёт в Git). Нажимать `helm upgrade` больше не нужно — нужно сделать коммит.
:::

Это обзор без практики — дальше идут сильные направления, к которым ты теперь подготовлена:

- **GitOps (Argo CD, Flux).** Chart или Kustomize-оверлей лежит в Git; контроллер в кластере следит за репозиторием и применяет изменения. Откат — `git revert`. Результат: любое состояние кластера объяснимо историей коммитов.
- **Операторы.** Ты уже встречала идею: Prometheus Operator (шаг 11.3) добавляет объекты `ServiceMonitor`. Оператор — контроллер, знающий, как «правильно эксплуатировать» сложное приложение (БД, брокер), и управляемый через CRD. Для PostgreSQL — CloudNativePG, Zalando, для RabbitMQ — свой оператор.
- **Gateway API.** Преемник `Ingress`: роли разделены (инфраструктурщик определяет `Gateway`, команда приложения — `HTTPRoute`), богаче маршрутизация. Traefik его поддерживает; на новых кластерах всё чаще пишут `HTTPRoute`, а не `Ingress`.
- **Сервис-меш и политика.** Istio/Linkerd (шифрование между Pod, наблюдаемость), Kyverno/OPA Gatekeeper (политики приёма, шаг 9.6).
- **Управляемый Kubernetes.** EKS, GKE, AKS, Yandex Managed Kubernetes: всё, что ты прошла, работает так же, но control plane обслуживает провайдер, а `LoadBalancer`, диски и автоскейлер узлов — настоящие.

### why
Без этого обзора курс закончился бы «умею выкатывать руками». Место, где Kubernetes реально используется, — это GitOps-конвейер: поэтому полезно знать названия, чтобы понимать, что искать.

### quiz
- Чем GitOps отличается от запуска `helm upgrade` с ноутбука?
- Какую задачу решает оператор?

### links
- https://argo-cd.readthedocs.io/ | Argo CD | Argo CD
- https://fluxcd.io/ | Flux | Flux
- https://gateway-api.sigs.k8s.io/ | Gateway API | Gateway API

## 15.7 🔨 Production Hell 2: релиз с пятью поломками | short: 🔨 Production Hell 2 | est: ~60 мин
### intro
**Слова шага:** *многослойная поломка релиза*, *диагностика без подсказок*, *чинить chart, а не кластер*.

:::tip Если совсем просто
Теперь без страховки: тебе передали релиз, на котором висит табличка «не работает», и нет ни одной подсказки, где именно. Правило из шага 8.7 остаётся: чини по одной, после каждой правки смотри, изменился ли симптом. Новое правило: **чинить нужно chart или значения, а не кластер** — поправка «руками» исчезнет при следующем `upgrade`.
:::

Ставим «испорченную» копию chart’а в отдельный namespace (в нём пять независимых поломок: каждая — по одной на слой, которые ты изучала):

```bash run
cd ~/kubernetes-lab
rm -rf hell && cp -R charts/coffeeshop hell && cd hell
rm -f Chart.lock && rm -rf charts && mkdir charts
for c in coffeeshop-db coffeeshop-api coffeeshop-web; do cp -R ../charts/$c charts/$c; done
python3 - <<'PY'
import re
def sub(p, a, b):
    s = open(p).read(); assert a in s, (p, a); open(p, 'w').write(s.replace(a, b, 1))
# 1. Service API смотрит на несуществующий порт
sub('charts/coffeeshop-api/values.yaml', 'targetPort: 3000', 'targetPort: 3300')
# 2. пробы — на путь, которого нет
sub('charts/coffeeshop-api/values.yaml', 'path: /health', 'path: /healthz')
# 3. память ниже минимально возможной
sub('charts/coffeeshop-api/values.yaml', 'limits: {memory: 256Mi}', 'limits: {memory: 16Mi}')
# 4. имя хоста базы с опечаткой
sub('values.yaml', 'db: {host: db}', 'db: {host: db-primary}')
# 5. Ingress пишет в другой класс
sub('charts/coffeeshop-web/values.yaml', 'className: traefik', 'className: nginx')
PY
sed -i.bak '/^dependencies:/,$d' Chart.yaml && rm -f Chart.yaml.bak
helm upgrade --install hell . -n hell --create-namespace --set global.dbPassword=s3cret 2>&1 | tail -2
sleep 45
kubectl get pods,svc,ingress -n hell
curl -s -o /dev/null -w "shop (Host: hell.localhost): HTTP %{http_code}\n" -H 'Host: shop.localhost' http://localhost/
```

### result
```out auto
```

**Задание:** найди и исправь все пять поломок, **не** редактируя объекты в кластере (`kubectl edit`/`patch` не использовать). Чини файлы в `~/kubernetes-lab/hell/` и применяй `helm upgrade`. Инструменты: `kubectl get`, `describe`, `logs`, `get events`, `helm template`, `helm get manifest`, таблица шага 8.6. Намёки по слоям (не по поломкам): *сеть Service → Pod*, *проверка готовности*, *ресурсы*, *связь с БД*, *маршрутизация снаружи*. Подсказка-тест: когда всё починено, `kubectl get pods -n hell` — всё `Running` и `READY`, а адрес сайта отвечает `200`.

Когда закончила — проверь и убери:

```bash run
cd ~/kubernetes-lab
kubectl get pods -n hell
helm uninstall hell -n hell
kubectl delete namespace hell
```

### result
```out auto
```

### why
Пять поломок в разных слоях стоят ровно того, чтобы повторить урок шага 8.7 на уровне Helm: симптом (`CrashLoopBackOff`, `503`, `404`) почти никогда не говорит, в каком слое причина. Выигрывает тот, кто идёт по слоям сверху вниз и проверяет **конкретным запросом** (`kubectl get endpoints`, `describe`, логи), а не гадает.

### deep Если не получилось
- **Починила одно, но симптом остался** — значит, есть вторая причина того же симптома; перепроверь на каждом слое отдельно.
- **Совсем застряла** — в таблицу шага 8.6 и в справку «Типичные ошибки» вынесены симптомы; ответы специально не приводятся.

### quiz
- Почему нельзя чинить поломки через `kubectl edit`?
- В каком порядке идти по слоям при `503` на входе?

### links
- https://kubernetes.io/docs/tasks/debug/debug-application/ | отладка приложений | Kubernetes: Debug Applications

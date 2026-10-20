# Сессия 13 · Шаблоны Helm
dur: ~4 ч

## 13.1 Синтаксис `{{ }}` и встроенные объекты | short: Синтаксис шаблонов | est: ~35 мин
### intro
**Слова шага:** *Go template*, *действие `{{ }}`*, *контекст `.`*, *`.Values`*, *`.Release`*, *`.Chart`*, *обрезка пробелов `{{-`*.

:::tip Если совсем просто
Шаблон — письмо с пустыми местами: «Уважаемая `{{ имя }}`!». Всё вне двойных фигурных скобок остаётся как есть, а внутри скобок Helm вычисляет значение и вставляет его. Точка `.` — это «папка с данными, которая сейчас у меня в руках»: из неё берём `.Values`, `.Release`, `.Chart`.
:::

```svg
@template-form
```

Чтобы пробовать синтаксис, не рискуя настоящим chart’ом, сделаем «игровую площадку» — chart из одного ConfigMap, который мы только **распечатываем** через `helm template`:

```bash run
cd ~/kubernetes-lab/charts
helm create playground >/dev/null
rm -rf playground/templates/* && : > playground/values.yaml
cat > playground/values.yaml <<'EOF'
appName: coffeeshop
replicas: 2
debug: false
tags: [web, api]
limits: {cpu: 500m, memory: 256Mi}
EOF
cat > playground/templates/cm.yaml <<'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ .Release.Name }}-demo
data:
  release: {{ .Release.Name }}
  namespace: {{ .Release.Namespace }}
  chart: {{ .Chart.Name }}-{{ .Chart.Version }}
  app: {{ .Values.appName }}
  replicas: "{{ .Values.replicas }}"
EOF
helm template shop playground --namespace demo
```

### result
```out auto
```

Встроенные объекты:

| Объект | Содержит |
|---|---|
| `.Values` | значения: `values.yaml` + `-f` + `--set` |
| `.Release` | `.Name`, `.Namespace`, `.Revision`, `.IsInstall`, `.IsUpgrade` |
| `.Chart` | поля `Chart.yaml` (`.Name`, `.Version`, `.AppVersion`) — с большой буквы |
| `.Capabilities` | версия Kubernetes и доступные API (для условий «если кластер новее») |
| `.Template` | имя текущего файла шаблона |

**Пробелы и переводы строк.** Скобка `{{-` «съедает» пробельные символы **слева** от себя (включая перевод строки), `-}}` — справа. Это пригодится в следующих шагах: `if` и `range` оставляют после себя пустые строки, и без `-` YAML получится с дырами или со съехавшими отступами.

### why
Весь Helm — это подстановка данных в текст. Если хорошо понимать, что в каждый момент лежит в `.`, то никакая директива не будет «магией». Привычка №1: сомневаешься — выведи значение как есть через `{{ .Values | toYaml }}` или `helm template --debug`.

### deep Если не получилось
- **`nil pointer evaluating interface {}.appName`** — в `values.yaml` нет такого ключа или он на другом уровне; регистр важен (`appName` ≠ `appname`).
- **Строка `replicas: "2"` в кавычках, хотя число** — в ConfigMap все значения строки, поэтому мы сознательно взяли в кавычки.

### quiz
- Что делают `{{-` и `-}}`?
- Чем `.Release.Name` отличается от `.Chart.Name`?
- Что такое точка `.` в начале выражения?

### links
- https://helm.sh/docs/chart_template_guide/builtin_objects/ | встроенные объекты | Helm: Built-in Objects
- https://pkg.go.dev/text/template | Go templates | Go: text/template

## 13.2 Функции и pipeline | short: Функции и pipeline | est: ~40 мин
### intro
**Слова шага:** *функция*, *pipeline (`|`)*, *`default`*, *`quote`*, *`upper`*, *`toYaml`*, *`nindent`*, *`required`*.

:::tip Если совсем просто
Pipeline — конвейер на кухне: сырьё идёт по ленте и проходит обработку на каждой станции. `{{ .Values.appName | upper | quote }}` читается слева направо: взяли значение → сделали заглавными → поставили в кавычки. Каждая станция принимает результат предыдущей.
:::

В Helm около сотни функций (шаблонизатор Go + библиотека Sprig). Нужны в основном семь:

| Функция | Что делает | Пример |
|---|---|---|
| `default` | подставляет запасное значение | `{{ .Values.tag \| default "v1" }}` |
| `quote` | оборачивает в кавычки | `{{ .Values.name \| quote }}` |
| `upper` / `lower` | регистр | `{{ .Values.env \| upper }}` |
| `toYaml` | превращает структуру в YAML-текст | `{{ toYaml .Values.limits }}` |
| `nindent N` | перевод строки + отступ N пробелов | `{{ toYaml .Values.limits \| nindent 4 }}` |
| `required` | падает с понятным сообщением, если значение пусто | `{{ required "нужен пароль" .Values.password }}` |
| `trunc`, `trimSuffix` | обрезка (имена ≤ 63 символа) | `{{ .Release.Name \| trunc 40 }}` |

```bash run
cd ~/kubernetes-lab/charts
cat > playground/templates/cm.yaml <<'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ .Release.Name }}-demo
data:
  app-upper: {{ .Values.appName | upper | quote }}
  tag: {{ .Values.tag | default "v1" | quote }}
  limits: |-
    {{- toYaml .Values.limits | nindent 4 }}
  password: {{ required "задай password через --set" .Values.password | quote }}
EOF
echo "--- без password:"; helm template shop playground 2>&1 | head -3
echo "--- с password:";   helm template shop playground --set password=secret
```

### result
```out auto
```

Без `password` Helm останавливается **до обращения к кластеру** с твоим текстом ошибки (`required`). Это лучший способ не выкатить chart без обязательного значения. Цепочка `toYaml | nindent 4` — главный приём chart’ов: словарь из values превращается в YAML и вставляется с нужным отступом. Конструкция `|-` в YAML — многострочная строка без завершающего перевода.

### why
Три функции решают 90 % задач: `default` (разумное умолчание), `required` (обязательное значение), `toYaml | nindent` (вставка целого блока вроде `resources`). Отступ в `nindent` — число пробелов, на которое вставляемый блок должен быть сдвинут **в итоговом файле**; ошибка в нём — самая частая поломка шаблонов (шаг 13.8).

### deep Команды по частям
`nindent 4` = «перевод строки, затем каждая строка сдвинута на 4 пробела». Существует и `indent 4` (без перевода строки в начале), но с `{{-` слева практически везде нужен именно `nindent`. `toYaml` в Helm 4 и Helm 3 одинаков.

### deep Если не получилось
- **`function "toYaml" not defined`** — функция написана с ошибкой в регистре (`toyaml`); имена функций чувствительны к регистру.
- **Лишняя пустая строка в результате** — забыт `-` в `{{-`.

### quiz
- В чём преимущество `required` перед `default` для пароля?
- Что делает цепочка `toYaml | nindent 4`?
- В какой последовательности выполняется `{{ x | f | g }}`?

### links
- https://helm.sh/docs/chart_template_guide/functions_and_pipelines/ | функции | Helm: Template Functions and Pipelines
- https://masterminds.github.io/sprig/ | Sprig | Sprig: функции

## 13.3 if, with, range | short: Условия и циклы | est: ~40 мин
### intro
**Слова шага:** *`if`/`else`*, *`with`*, *`range`*, *пустое значение как «ложь»*, *`$` — корневой контекст*.

:::tip Если совсем просто
`if` — «если в анкете это поле заполнено, напиши абзац». `with` — «возьми вот эту папку и дальше работай только внутри неё», `range` — «для каждого листа в стопке сделай одно и то же». «Ложью» считается всё пустое: `false`, `0`, пустая строка, пустой список и словарь, отсутствующий ключ.
:::

```bash run
cd ~/kubernetes-lab/charts
cat > playground/templates/cm.yaml <<'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ .Release.Name }}-demo
data:
  {{- if .Values.debug }}
  logLevel: debug
  {{- else }}
  logLevel: info
  {{- end }}
  {{- with .Values.limits }}
  cpu: {{ .cpu }}
  memory: {{ .memory }}
  release: {{ $.Release.Name }}
  {{- end }}
  tags: |-
    {{- range .Values.tags }}
    - {{ . }}
    {{- end }}
  {{- range $key, $val := .Values.limits }}
  limit-{{ $key }}: {{ $val | quote }}
  {{- end }}
EOF
echo "=== debug: false"; helm template shop playground
echo "=== debug: true";  helm template shop playground --set debug=true | grep logLevel
```

### result
```out auto
```

Что здесь важно:

- **`if`**: `debug: false` → ветка `else`; ключ можно писать, не вводя в `values.yaml` вовсе (отсутствие = ложь).
- **`with`** меняет `.`: внутри блока `.cpu` — это `.Values.limits.cpu`. Чтобы обратиться к корню (`.Release`), нужно `$` — **всегда указывает на корневой контекст** (`$.Release.Name`). Забытый `$` внутри `with`/`range` — частая ошибка: «nil pointer», хотя значение «вроде бы есть».
- **`range` по списку** — `.` на каждом шаге равен элементу; **по словарю** (`$key, $val := …`) — ключ и значение (словари перебираются в алфавитном порядке ключей, поэтому результат стабилен).

### why
Условия делают chart гибким: «создавай Ingress, только если `ingress.enabled`». Циклы — чтобы не писать десять переменных окружения руками: список в `values.yaml`, цикл в шаблоне. Правило хорошего тона: `values.yaml` должен быть *плоским и понятным*, а логику (если/то) держать в шаблонах.

### deep Если не получилось
- **Вместо одного элемента напечатался весь список целиком** — внутри `range` забыл, что `.` изменилась; печатай `{{ . }}`.
- **`range` не выводит ничего** — список пуст или ключ в другом месте `values`: проверь `helm template --debug` или `{{ .Values | toYaml }}`.

### quiz
- Что считается «ложью» в `if`?
- Как обратиться к `.Release.Name` из блока `with`?
- Чем `range` по списку отличается от `range` по словарю?

### links
- https://helm.sh/docs/chart_template_guide/control_structures/ | управляющие конструкции | Helm: Flow Control
- https://helm.sh/docs/chart_template_guide/variables/ | переменные | Helm: Variables

## 13.4 define, include и _helpers.tpl | short: Общие вставки | est: ~35 мин
### intro
**Слова шага:** *`define`*, *`include`*, *`template`*, *именованный шаблон*, *labels*, *`_helpers.tpl`*.

:::tip Если совсем просто
Если одну и ту же фразу («метки приложения: имя, версия, кто развернул») приходится писать в Deployment, Service и Secret — вынеси её в отдельную карточку-заготовку с названием и вставляй по названию. Поменяла карточку один раз — поменялось везде.
:::

В файле `templates/_helpers.tpl` (подчёркивание → не превращается в объект) объявляем именованные шаблоны. Вернём их в наш `coffeeshop-api`:

```bash run
cd ~/kubernetes-lab/charts
cat > coffeeshop-api/templates/_helpers.tpl <<'EOF'
{{/* Имя ресурсов: <релиз>-api, не длиннее 63 символов */}}
{{- define "coffeeshop-api.fullname" -}}
{{- printf "%s-api" .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{/* Метки, общие для всех объектов */}}
{{- define "coffeeshop-api.labels" -}}
app.kubernetes.io/name: coffeeshop-api
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end }}

{{/* Метки для селекторов (меняться не должны) */}}
{{- define "coffeeshop-api.selectorLabels" -}}
app.kubernetes.io/name: coffeeshop-api
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
EOF
cat > coffeeshop-api/templates/service.yaml <<'EOF'
apiVersion: v1
kind: Service
metadata:
  name: {{ include "coffeeshop-api.fullname" . }}
  labels:
    {{- include "coffeeshop-api.labels" . | nindent 4 }}
spec:
  selector:
    {{- include "coffeeshop-api.selectorLabels" . | nindent 4 }}
  ports:
    - port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.targetPort }}
EOF
helm template demo coffeeshop-api -s templates/service.yaml
```

### result
```out auto
```

`define "имя"` объявляет шаблон; `include "имя" .` вызывает его **и возвращает текст**, который можно пустить дальше по pipeline (`| nindent 4`). Вторая форма, `{{ template "имя" . }}`, печатает напрямую и в pipeline не годится — поэтому везде используют `include`. Точка `.` в вызове — передача контекста: без неё внутри шаблона не будет ни `.Release`, ни `.Values`.

Разделение меток на `labels` и `selectorLabels` — не прихоть: **селектор Deployment нельзя менять после создания** (иначе Kubernetes отвергнет обновление, шаг 4.1), поэтому в нём — только неизменяемое; а версия chart’а меняется каждый релиз и живёт только в обычных `labels`.

### why
Без общих вставок chart быстро обрастает расхождениями: в одном месте поменяли метку, в другом забыли. Метки `app.kubernetes.io/*` — общепринятый стандарт, по которому понимают приложение инструменты (`kubectl`, Prometheus, дашборды).

### deep Если не получилось
- **`template: no template "coffeeshop-api.fullname" associated`** — имя в `include` не совпало с `define` (опечатка) или `_helpers.tpl` не сохранён.
- **Лишняя пустая строка внутри меток** — не хватает `-` в `{{- define … -}}`.

### quiz
- Чем `include` лучше `template`?
- Зачем в `include` передавать `.`?
- Почему `selectorLabels` вынесены отдельно от `labels`?

### links
- https://helm.sh/docs/chart_template_guide/named_templates/ | именованные шаблоны | Helm: Named Templates
- https://kubernetes.io/docs/concepts/overview/working-with-objects/common-labels/ | рекомендованные метки | Kubernetes: Recommended Labels

## 13.5 Шаблоны API целиком: пробы, ресурсы, Ingress по флагу | short: API-chart целиком | est: ~45 мин
### intro
**Слова шага:** *`resources` из values*, *`probes`*, *Ingress по флагу `ingress.enabled`*, *`.Capabilities`*.

:::tip Если совсем просто
Собираем шаблон «в боевом виде»: все настраиваемые части вынесены в `values.yaml`, а необязательные объекты (Ingress) включаются выключателем — по умолчанию его нет, но можно включить одной строкой в `values`.
:::

```bash run
cd ~/kubernetes-lab/charts
cat > coffeeshop-api/values.yaml <<'EOF'
replicaCount: 2
image:
  repository: coffeeshop-api
  tag: v1
service:
  port: 80
  targetPort: 3000
db:
  host: db
  user: coffeeshop
  name: coffeeshop
  password: ""          # обязательный: задаётся при установке, не хранится здесь
resources:
  requests: {cpu: 100m, memory: 128Mi}
  limits: {memory: 256Mi}
probes:
  path: /health
ingress:
  enabled: false
  host: shop.localhost
  className: traefik
EOF
cat > coffeeshop-api/templates/secret.yaml <<'EOF'
apiVersion: v1
kind: Secret
metadata:
  name: {{ include "coffeeshop-api.fullname" . }}
  labels:
    {{- include "coffeeshop-api.labels" . | nindent 4 }}
type: Opaque
stringData:
  DB_PASSWORD: {{ required "задай db.password (--set db.password=…)" .Values.db.password | quote }}
EOF
cat > coffeeshop-api/templates/deployment.yaml <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "coffeeshop-api.fullname" . }}
  labels:
    {{- include "coffeeshop-api.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "coffeeshop-api.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "coffeeshop-api.selectorLabels" . | nindent 8 }}
      annotations:
        checksum/secret: {{ include (print $.Template.BasePath "/secret.yaml") . | sha256sum }}
    spec:
      containers:
        - name: api
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          ports:
            - containerPort: {{ .Values.service.targetPort }}
          env:
            - {name: DB_HOST, value: {{ .Values.db.host | quote }}}
            - {name: DB_USER, value: {{ .Values.db.user | quote }}}
            - {name: DB_NAME, value: {{ .Values.db.name | quote }}}
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: {{ include "coffeeshop-api.fullname" . }}
                  key: DB_PASSWORD
          readinessProbe:
            httpGet: {path: {{ .Values.probes.path }}, port: {{ .Values.service.targetPort }}}
            periodSeconds: 5
          livenessProbe:
            httpGet: {path: {{ .Values.probes.path }}, port: {{ .Values.service.targetPort }}}
            initialDelaySeconds: 10
            periodSeconds: 10
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
EOF
cat > coffeeshop-api/templates/ingress.yaml <<'EOF'
{{- if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "coffeeshop-api.fullname" . }}
  labels:
    {{- include "coffeeshop-api.labels" . | nindent 4 }}
spec:
  ingressClassName: {{ .Values.ingress.className }}
  rules:
    - host: {{ .Values.ingress.host | quote }}
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: {{ include "coffeeshop-api.fullname" . }}
                port: {number: {{ .Values.service.port }}}
{{- end }}
EOF
helm lint coffeeshop-api --set db.password=x
echo "--- без пароля:"; helm template demo coffeeshop-api 2>&1 | head -2
echo "--- ресурсы в Deployment:"; helm template demo coffeeshop-api --set db.password=x -s templates/deployment.yaml | grep -A5 'resources:'
echo "--- Ingress выключен/включён:"
helm template demo coffeeshop-api --set db.password=x | grep -c 'kind: Ingress'
helm template demo coffeeshop-api --set db.password=x --set ingress.enabled=true | grep -c 'kind: Ingress'
```

### result
```out auto
```

Два красивых приёма в этом шаблоне:

- **`checksum/secret`** — хеш содержимого Secret в аннотации Pod. Менялся пароль → меняется хеш → меняется шаблон Pod → Deployment делает rolling update. Без этого Pod не знают, что Secret/ConfigMap поменялись, и продолжают работать со старыми значениями (ловушка шага 7.2).
- **`{{- if .Values.ingress.enabled }} … {{- end }}`** вокруг всего файла: при выключателе `false` файл превращается в пустоту, и объекта нет.

Пароль хранится **не** в `values.yaml` (пустая строка + `required`): обязательно задаётся при установке, и забыть его нельзя.

### why
Теперь один chart обслуживает любое окружение: отличия — только в значениях (число реплик, ресурсы, включён ли Ingress). Это то, ради чего Helm и нужен; в сессии 14 вынесем отличия в отдельные файлы `values-dev/prod`.

### deep Если не получилось
- **`include (print $.Template.BasePath "/secret.yaml") .`: `error calling include`** — путь указан неверно; он строится от `$.Template.BasePath` (то есть `coffeeshop-api/templates`), файл должен называться ровно `secret.yaml`.
- **`helm lint` ругается на `icon is recommended`** — это лишь информационное сообщение (`[INFO]`), не ошибка.

### quiz
- Для чего аннотация `checksum/secret` в шаблоне Pod?
- Как сделать так, чтобы Ingress создавался только по требованию?
- Почему пароль БД не лежит в `values.yaml` со значением?

### links
- https://helm.sh/docs/howto/charts_tips_and_tricks/#automatically-roll-deployments | авто-перезапуск при смене конфигурации | Helm: Automatically Roll Deployments
- https://helm.sh/docs/chart_best_practices/values/ | лучшие практики values | Helm: Best Practices for Values

## 13.6 Chart для PostgreSQL: StatefulSet, PVC, Secret | short: Chart для БД | est: ~45 мин
### intro
**Слова шага:** *второй chart*, *`volumeClaimTemplates`*, *`StatefulSet`*, *`required`*, *имя Service = имя релиза*.

:::tip Если совсем просто
Второй рецепт — для базы. Его особенность: данные должны пережить Pod (том из сессии 6) и у базы стабильное имя. Рецепт делаем по той же раскладке, что и для API: паспорт, значения, три чертежа (Secret, Service, StatefulSet).
:::

```bash run
cd ~/kubernetes-lab/charts
helm create coffeeshop-db >/dev/null
rm -rf coffeeshop-db/templates/* && : > coffeeshop-db/values.yaml
cat > coffeeshop-db/Chart.yaml <<'EOF'
apiVersion: v2
name: coffeeshop-db
description: PostgreSQL для CoffeeShop
type: application
version: 0.1.0
appVersion: "18"
EOF
cat > coffeeshop-db/values.yaml <<'EOF'
image:
  repository: postgres
  tag: "18"
auth:
  user: coffeeshop
  database: coffeeshop
  password: ""          # обязательный
storage:
  size: 1Gi
  storageClass: ""      # пусто = класс по умолчанию
resources:
  requests: {cpu: 100m, memory: 256Mi}
  limits: {memory: 512Mi}
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
  POSTGRES_PASSWORD: {{ required "задай auth.password (--set auth.password=…)" .Values.auth.password | quote }}
EOF
cat > coffeeshop-db/templates/service.yaml <<'EOF'
apiVersion: v1
kind: Service
metadata:
  name: {{ .Release.Name }}
spec:
  clusterIP: None
  selector:
    app: {{ .Release.Name }}
  ports:
    - {name: postgres, port: 5432}
EOF
cat > coffeeshop-db/templates/statefulset.yaml <<'EOF'
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: {{ .Release.Name }}
spec:
  serviceName: {{ .Release.Name }}
  replicas: 1
  selector:
    matchLabels:
      app: {{ .Release.Name }}
  template:
    metadata:
      labels:
        app: {{ .Release.Name }}
    spec:
      containers:
        - name: postgres
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          envFrom:
            - secretRef:
                name: {{ .Release.Name }}-auth
          env:
            - {name: PGDATA, value: /var/lib/postgresql/data/pgdata}
          ports:
            - {containerPort: 5432, name: postgres}
          readinessProbe:
            exec:
              command: ["sh", "-c", "pg_isready -U $POSTGRES_USER -d $POSTGRES_DB"]
            periodSeconds: 5
          volumeMounts:
            - {name: data, mountPath: /var/lib/postgresql}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: [ReadWriteOnce]
        {{- with .Values.storage.storageClass }}
        storageClassName: {{ . | quote }}
        {{- end }}
        resources:
          requests:
            storage: {{ .Values.storage.size }}
EOF
helm lint coffeeshop-db --set auth.password=x
helm template db coffeeshop-db --set auth.password=x | grep -E '^kind:|storage:|name: db'
```

### result
```out auto
```

Примечания к шаблону. `clusterIP: None` — headless Service (шаг 6.5): DNS-имя `db` резолвится напрямую в Pod, как нужно StatefulSet. Имя Service равно **имени релиза**: ставим `helm install db …` → API находит базу по `DB_HOST=db`, как и во всех предыдущих сессиях. Блок `{{- with .Values.storageClass }}` — `storageClassName` пишется только если значение задано, иначе используется класс по умолчанию (шаг 6.2). Образ PostgreSQL 18 хранит данные в подкаталоге `/var/lib/postgresql`, поэтому том монтируется именно туда, а не в `/data` (стандарт сайта).

### why
Chart БД не зависит от chart’а API: их можно ставить, обновлять и **удалять независимо**. Особенно важно второе: `helm uninstall` для API не должен трогать данные. (PVC, созданные `volumeClaimTemplates`, Helm при `uninstall` **не удаляет** — это защита данных; удалять их придётся вручную и осознанно.)

### deep Если не получилось
- **`storageClassName: ""` ломает привязку тома** — пустая строка означает «без класса», не «по умолчанию». Поэтому условие `with`: не писать поле вовсе, пока значение не задано.

### quiz
- Почему имя Service базы равно имени релиза?
- Что произойдёт с данными БД при `helm uninstall db`?
- Зачем нужен блок `with` вокруг `storageClassName`?

### links
- https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/#volume-claim-templates | volumeClaimTemplates | Kubernetes: StatefulSet Volume Claim Templates
- https://helm.sh/docs/howto/charts_tips_and_tricks/#using-the-required-function | required | Helm: Using the required function

## 13.7 Зависимости и subcharts | short: Subcharts | est: ~40 мин
### intro
**Слова шага:** *зависимость (`dependencies`)*, *subchart*, *`helm dependency update`*, *`condition`*, *передача values родителю → ребёнку*.

:::tip Если совсем просто
Дом (родительский chart) может включать квартиры (subcharts): каждая квартира — самостоятельный chart со своей планировкой, но все живут под одной крышей и ставятся одной командой. Жильцам можно передать пожелания «сверху»: в values родителя пишется раздел с именем квартиры.
:::

```svg
@umbrella-subcharts
```

Соберём «зонтичный» (umbrella) chart `coffeeshop`, зависящий от двух наших chart’ов. Подробнее — в сессии 15; сейчас механика:

```bash run
cd ~/kubernetes-lab/charts
mkdir -p coffeeshop && cd coffeeshop
cat > Chart.yaml <<'EOF'
apiVersion: v2
name: coffeeshop
description: Весь CoffeeShop одним релизом
type: application
version: 0.1.0
appVersion: "v1"
dependencies:
  - name: coffeeshop-api
    version: 0.1.0
    repository: "file://../coffeeshop-api"
  - name: coffeeshop-db
    version: 0.1.0
    repository: "file://../coffeeshop-db"
EOF
cat > values.yaml <<'EOF'
coffeeshop-api:
  db:
    host: coffee-db
coffeeshop-db: {}
EOF
helm dependency update
ls charts
helm template coffee . --set coffeeshop-api.db.password=x --set coffeeshop-db.auth.password=x | grep -E '^kind:|^  name:' | head -12
```

### result
```out auto
```

`helm dependency update` упаковал subcharts в `charts/*.tgz` и создал `Chart.lock` (точные версии — как `package-lock.json`). Значения передаются так: всё под ключом с именем subchart’а в `values.yaml` родителя попадает в `.Values` ребёнка (`coffeeshop-api.db.host` → `.Values.db.host` внутри API). Заметь проблему, которую увидишь в выводе: имена объектов строятся от `.Release.Name`, поэтому оба chart’а получат `coffee-api` и `coffee` — а нам нужна база с именем `db`. В шаге 15.2 научимся задавать имена через значения и общие `global`-значения; сейчас фиксируем главное — **механику зависимостей**.

Ещё три рабочих инструмента для зависимостей:

- `condition: coffeeshop-db.enabled` в `dependencies` — включать subchart по флагу (удобно, если в проде база внешняя).
- `alias:` — поставить один и тот же chart дважды под разными именами.
- `global:` в values родителя — значения, видимые **всем** subcharts (`.Values.global.…`).

### why
Umbrella chart даёт установку всего приложения одной командой и единую версию набора. Subchart остаётся независимым: его можно ставить и отдельно (как в 13.6). Таким же способом подключают чужие chart’ы: например, `postgresql` из каталога вместо собственного.

### deep Если не получилось
- **`Error: directory ../coffeeshop-api not found`** — запускай `helm dependency update` из папки `coffeeshop`, и chart’ы-соседи должны лежать в `charts/`, как мы создавали.
- **`Chart.lock is out of sync`** — после правки `dependencies` повтори `helm dependency update`.

### quiz
- Как значения из родительского chart’а попадают в subchart?
- Что хранит `Chart.lock`?
- Для чего нужен `condition` у зависимости?

### links
- https://helm.sh/docs/chart_template_guide/subcharts_and_globals/ | subcharts и global | Helm: Subcharts and Global Values
- https://helm.sh/docs/helm/helm_dependency/ | helm dependency | Helm: helm dependency

## 13.8 🔨 Неверный nindent: валидный шаблон, невалидный YAML | short: 🔨 nindent | est: ~35 мин
### intro
**Слова шага:** *`nindent`*, *`indent`*, *сдвинутый блок*, *`error converting YAML to JSON`*.

:::tip Если совсем просто
Список покупок, в котором строка попала не под ту рубрику: слова верные, а смысл поплыл. С `nindent` то же самое: блок значений вставлен правильный, но с неправильным отступом, и YAML «ссылается» не на то место.
:::

Сломаем отступ `resources` в Deployment: вместо `nindent 12` — `nindent 6`.

```bash run
cd ~/kubernetes-lab/charts
cp coffeeshop-api/templates/deployment.yaml /tmp/deployment.yaml.bak
sed -i.bak 's/toYaml .Values.resources | nindent 12/toYaml .Values.resources | nindent 6/' coffeeshop-api/templates/deployment.yaml
helm lint coffeeshop-api --set db.password=x 2>&1 | head -6
helm template demo coffeeshop-api --set db.password=x 2>&1 | head -4
echo "--- как это выглядит в готовом файле:"
helm template demo coffeeshop-api --set db.password=x --debug 2>&1 | grep -B3 -A4 'requests:' | head -14
```

### result
```out auto
```

Шаблон «правильный» с точки зрения Go, но готовый документ получается с `requests:` на уровне `spec`, а не `resources`; Helm сообщает `error converting YAML to JSON` или `mapping values are not allowed`. Разбор: читай **готовый** YAML (`--debug`), найди строку из сообщения и посмотри на отступы выше. Вторая типичная ошибка того же рода — `indent` вместо `nindent`: блок «приклеивается» к предыдущей строке. Чиним и проверяем:

```bash run
cd ~/kubernetes-lab/charts
cp /tmp/deployment.yaml.bak coffeeshop-api/templates/deployment.yaml
rm -f coffeeshop-api/templates/deployment.yaml.bak
helm lint coffeeshop-api --set db.password=x
```

### result
```out auto
```

**Приёмка сессии:** CoffeeShop (API + БД) ставится двумя chart’ами в один namespace и отвечает:

```bash run
cd ~/kubernetes-lab/charts
kubectl create namespace shop-helm
helm install db coffeeshop-db -n shop-helm --set auth.password=s3cret
helm install api coffeeshop-api -n shop-helm --set db.password=s3cret --set db.host=db --set image.tag=v1
kubectl rollout status statefulset/db -n shop-helm --timeout=120s
kubectl rollout status deployment/api-api -n shop-helm --timeout=120s
kubectl get pods,svc,pvc -n shop-helm
kubectl exec -n shop-helm deploy/api-api -- wget -qO- -T 3 http://localhost:3000/health
```

### result
```out auto
```

(Имя `api-api` — потому что релиз называется `api`, а шаблон добавляет `-api`; это и подсказка улучшить `fullname`, что мы сделаем в 15.2.) Убираем, **сохранив** тома для проверки: `helm uninstall api db -n shop-helm`, затем `kubectl get pvc -n shop-helm` — PVC на месте; удаляем их вручную: `kubectl delete namespace shop-helm`.

### why
Из всех ошибок шаблонов именно отступы дают самые путаные сообщения, потому что ошибка не в том месте, куда указывает Helm. Единственное надёжное лекарство — смотреть сгенерированный YAML и считать пробелы от ключа-родителя.

### deep Если не получилось
- **БД не поднимается, PVC в `Pending`** — смотри шаг 6.7: класс хранения и режим доступа.
- **`api-api` в `CrashLoopBackOff`** — сначала `kubectl logs`; чаще всего неверный `db.host` или пароль не совпадает с паролем БД (обе команды выше используют `s3cret`).

### quiz
- Почему `helm lint` может пройти, а `install` упасть из-за YAML?
- Как определить, какой отступ нужен `nindent`?
- Остаются ли PVC после `helm uninstall` StatefulSet’а и почему?

### links
- https://helm.sh/docs/chart_template_guide/yaml_techniques/ | техники YAML | Helm: YAML Techniques

# Сессия 12 · Helm, основы
dur: ~4 ч

## 12.1 Зачем Helm | short: Зачем Helm | est: ~25 мин
### intro
**Слова шага:** *Helm*, *chart*, *release*, *values*, *шаблон*.

:::tip Если совсем просто
Представь, что в кофейне тебе нужно открыть три одинаковые точки: «тест», «стейджинг», «прод». Манифесты из сессий 3–8 — это три тетради с рецептами, которые отличаются парой строк (число реплик, адрес, пароль). Каждый раз переписывать тетрадь — ошибки. Helm — это кофемашина с капсулами: рецепт (chart) один, а «капсула» (values) выбирает, что получится. И ещё он ведёт журнал заказов (release): что и когда сварено, можно вернуть прошлый вкус.
:::

```svg
@helm-capsule
```

Helm даёт три вещи сразу:

1. **Менеджер пакетов**: `helm install traefik traefik/traefik` — готовые чужие приложения одной командой (мы уже так ставили Traefik в 5.4 и мониторинг в 11.3).
2. **Шаблонизатор**: в манифестах вместо конкретных значений — `{{ .Values.replicas }}`; значения подставляются при установке.
3. **Учёт релизов**: Helm помнит, что установлено, с какими значениями, и умеет обновлять (`upgrade`) и откатывать (`rollback`).

Четыре термина, на которых строится всё остальное:

| Слово | Что это |
|---|---|
| **chart** | пакет: папка с шаблонами манифестов и значениями по умолчанию |
| **values** | настройки, подставляемые в шаблоны (`values.yaml`, `-f`, `--set`) |
| **release** | конкретная установка chart’а в кластер с именем (можно поставить один chart несколько раз) |
| **repository** | каталог chart’ов, откуда их скачивают (`helm repo add`) |

### why
Без Helm одно приложение в трёх окружениях — это три копии манифестов, которые расходятся. С Helm — один chart и три небольших файла значений. Это также единственный привычный способ ставить в кластер чужие системы (Prometheus, Traefik, PostgreSQL, Argo CD): их авторы публикуют chart’ы.

### quiz
- Чем chart отличается от release?
- Что такое values и где они применяются?
- Что даёт Helm кроме подстановки значений в YAML?

### links
- https://helm.sh/docs/intro/using_helm/ | Helm: основы | Helm: Using Helm

## 12.2 Установка и устройство Helm | short: Установка и архитектура | est: ~25 мин
### intro
**Слова шага:** *Helm 4*, *клиент без сервера*, *`kubeconfig`*, *Secret с релизом*, *Tiller (история)*.

:::tip Если совсем просто
Helm — это просто программа на твоём Mac, которая готовит манифесты и отправляет их в кластер так же, как это делает `kubectl`. Отдельного «сервера Helm» внутри кластера нет. Историю установок он хранит тоже в кластере — обычными Secret’ами в том же namespace, где установлен релиз.
:::

Helm установлен в шаге 1.4. Проверим версию и найдём, где лежит учёт релизов:

```bash run
helm version --short
helm list -A
kubectl get secrets -n traefik -l owner=helm
```

### result
```out auto
```

Вывод `helm list -A` — релизы `traefik` и (если ставилась сессия 11) `monitoring`. А секреты с меткой `owner=helm` и типом `helm.sh/release.v1` — это и есть «журнал»: в каждом — упакованное описание ревизии релиза (`sh.helm.release.v1.traefik.v1`, `…v2` — каждый `upgrade` добавляет новую). Поэтому `helm rollback` работает с любого компьютера, где есть доступ к кластеру.

**Про версии.** В этой лабе — Helm 4 (мажор вышел в ноябре 2025). Команды, которые мы используем (`install`, `upgrade`, `template`, `lint`, `rollback`), в Helm 3 и 4 выглядят одинаково; различия в основном «под капотом» (по умолчанию применение через server-side apply и новое поведение `--wait`) и в формате chart’ов v3 (`apiVersion: v2`), который работает в обеих. Если у тебя Helm 3 — всё проходится без изменений; места, где это важно, отмечены.

### deep Почему больше нет Tiller
В Helm 2 внутри кластера жил серверный компонент Tiller с широкими правами — это была дыра в безопасности. С Helm 3 его убрали: клиент работает с правами вашего `kubeconfig`, а значит, подчиняется RBAC из шага 9.1.

### quiz
- Где Helm хранит информацию об установленных релизах?
- Почему из Helm убрали серверный компонент Tiller?

### links
- https://helm.sh/docs/topics/architecture/ | архитектура | Helm: Architecture
- https://helm.sh/docs/overview/ | Helm 4 | Helm: Overview

## 12.3 Готовые chart’ы: поиск, значения, установка | short: Чужие chart’ы | est: ~35 мин
### intro
**Слова шага:** *`helm search`*, *`helm show values`*, *`helm install --set`*, *`helm uninstall`*, *Artifact Hub*.

:::tip Если совсем просто
Прежде чем собирать свою кофемашину, поучись пользоваться чужой. Открываем каталог (Artifact Hub), находим готовое приложение, смотрим список настроек (`show values`), выбираем нужные и ставим.
:::

Поставим простое приложение из чужого chart’а — `nginx` от Bitnami-подобных каталогов нестабилен по доступности образов, поэтому берём официальный репозиторий примеров `podinfo` (маленькое веб-приложение для демонстраций):

```bash run
helm repo add podinfo https://stefanprodan.github.io/podinfo
helm repo update
helm search repo podinfo
helm show values podinfo/podinfo | head -30
helm install demo podinfo/podinfo --namespace helm-demo --create-namespace --set replicaCount=2
helm list -n helm-demo
kubectl get pods,svc -n helm-demo
```

### result
```out auto
```

Что сделала одна команда: создала `Deployment` на две реплики и `Service`; релиз назван `demo`, ставится в namespace `helm-demo`. `--set replicaCount=2` переопределил значение по умолчанию (в `show values` оно `1`). Теперь посмотрим, как Helm запоминает, что мы поменяли:

```bash run
helm get values demo -n helm-demo
helm get values demo -n helm-demo --all | head -8
helm uninstall demo -n helm-demo
kubectl get pods -n helm-demo
```

### result
```out auto
```

`helm get values` показывает **только то, что ты переопределила** (`--all` — ещё и значения по умолчанию). `helm uninstall` удаляет всё, что создал релиз, одним действием — ни одного забытого объекта, в отличие от ручного `kubectl delete` по списку файлов.

### why
Привычка «сначала `show values`, потом `install`» экономит часы: все возможности chart’а перечислены в его значениях, без чтения шаблонов. Это же основной способ работать с chart’ами сторонних проектов в продакшне.

### deep Если не получилось
- **`Error: INSTALLATION FAILED: Kubernetes cluster unreachable`** — Helm использует тот же `kubeconfig`, что и `kubectl`; проверь `kubectl config current-context` (шаг 1.5).
- **Репозиторий недоступен** — chart можно установить и из локальной папки или архива (`helm install demo ./chart`); именно так мы поступим в следующих шагах.

### quiz
- Как узнать, какие настройки есть у чужого chart’а?
- Что показывает `helm get values` без `--all`?
- Что удаляет `helm uninstall`?

### links
- https://artifacthub.io/ | каталог chart’ов | Artifact Hub
- https://helm.sh/docs/helm/helm_install/ | helm install | Helm: helm install

## 12.4 helm create: анатомия chart’а | short: Структура chart’а | est: ~30 мин
### intro
**Слова шага:** *`Chart.yaml`*, *`values.yaml`*, *`templates/`*, *`_helpers.tpl`*, *`NOTES.txt`*, *`.helmignore`*.

:::tip Если совсем просто
Chart — это обычная папка с договорённостями о том, что где лежит, как схема здания: в этой комнате — паспорт здания, в той — настройки по умолчанию, в третьей — чертежи (шаблоны). `helm create` выдаёт пустое здание с типовой планировкой — можно разглядеть, что где.
:::

```bash run
cd ~/kubernetes-lab && mkdir -p charts && cd charts
helm create coffeeshop-api
find coffeeshop-api -type f | sort
echo "--- Chart.yaml:"; grep -v '^#' coffeeshop-api/Chart.yaml | grep -v '^$'
```

### result
```out auto
```

| Файл | Зачем |
|---|---|
| `Chart.yaml` | «паспорт»: имя, версия chart’а (`version`) и версия приложения (`appVersion`) |
| `values.yaml` | значения по умолчанию, которые можно переопределять |
| `templates/*.yaml` | шаблоны манифестов (Go template, шаг 13.1) |
| `templates/_helpers.tpl` | общие вставки; файл с `_` не превращается в манифест |
| `templates/NOTES.txt` | подсказка, которую Helm печатает после установки |
| `charts/` | зависимости (subcharts) |
| `.helmignore` | что не включать в упакованный chart |

Два номера в `Chart.yaml` часто путают: **`version`** — версия *упаковки* (меняется, когда правишь шаблоны), **`appVersion`** — версия *приложения* внутри (например, тег образа `v1`). Они независимы.

Типовой набор из `helm create` рассчитан на nginx и содержит много лишнего (`HPA`, `ServiceAccount`, тесты). Для нашего API соберём chart сами, поэтому очищаем заготовку:

```bash run
cd ~/kubernetes-lab/charts/coffeeshop-api
rm -f templates/*.yaml templates/NOTES.txt
rm -rf templates/tests
ls templates
: > values.yaml
```

### result
```out auto
```

Остался только `_helpers.tpl` (пригодится в 13.4); `values.yaml` пуст — заполним в следующем шаге.

### why
Знакомство с раскладкой нужно, чтобы уверенно открывать любой чужой chart: сперва `Chart.yaml` и `values.yaml`, потом шаблоны. Почти все chart’ы в мире устроены именно так.

### quiz
- Чем `version` отличается от `appVersion` в `Chart.yaml`?
- Почему файл `_helpers.tpl` не создаёт Kubernetes-объект?

### links
- https://helm.sh/docs/topics/charts/ | структура chart’а | Helm: Charts
- https://helm.sh/docs/chart_template_guide/getting_started/ | первый chart | Helm: Getting Started

## 12.5 Перенос Deployment и Service API в chart | short: Свой chart для API | est: ~45 мин
### intro
**Слова шага:** *шаблон*, *`.Values`*, *`.Release.Name`*, *`helm template`*, *`helm lint`*.

:::tip Если совсем просто
Берём наш рабочий манифест Deployment и Service для API (шаги 4.1, 3.4) и заменяем в нём всё, что может отличаться между окружениями, на «пробелы для заполнения» вида `{{ .Values.… }}`. Остальное остаётся как было. Сначала смотрим, во что шаблон превращается (`helm template`), и лишь потом ставим в кластер.
:::

```bash run
cd ~/kubernetes-lab/charts/coffeeshop-api
cat > Chart.yaml <<'EOF'
apiVersion: v2
name: coffeeshop-api
description: API кофейни CoffeeShop
type: application
version: 0.1.0
appVersion: "v1"
EOF
cat > values.yaml <<'EOF'
replicaCount: 2
image:
  repository: coffeeshop-api
  tag: v1
service:
  port: 80
  targetPort: 3000
db:
  host: db.default.svc.cluster.local
  user: coffeeshop
  name: coffeeshop
  password: temporary-plaintext-password
EOF
cat > templates/deployment.yaml <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}-api
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: {{ .Release.Name }}-api
  template:
    metadata:
      labels:
        app: {{ .Release.Name }}-api
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
                  name: {{ .Release.Name }}-api
                  key: DB_PASSWORD
EOF
cat > templates/service.yaml <<'EOF'
apiVersion: v1
kind: Service
metadata:
  name: {{ .Release.Name }}-api
spec:
  selector:
    app: {{ .Release.Name }}-api
  ports:
    - port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.targetPort }}
EOF
cat > templates/secret.yaml <<'EOF'
apiVersion: v1
kind: Secret
metadata:
  name: {{ .Release.Name }}-api
type: Opaque
stringData:
  DB_PASSWORD: {{ .Values.db.password | quote }}
EOF
cd .. && helm lint coffeeshop-api
helm template demo coffeeshop-api | head -40
```

### result
```out auto
```

`helm lint` проверяет структуру и синтаксис («0 chart(s) failed» — всё в порядке). `helm template demo coffeeshop-api` — «репетиция»: Helm вычисляет шаблоны и печатает итоговый YAML, **ничего не отправляя в кластер**. Сравни: везде, где был `{{ .Release.Name }}`, стоит `demo`; `| quote` обернул значения в кавычки (важно для строк вроде `"true"` или чисел, которые иначе YAML прочтёт как другой тип).

Откуда что берётся: **`.Values`** — значения из `values.yaml`, `-f` и `--set`; **`.Release.Name`** — имя релиза, которое ты задаёшь в `helm install <имя> …`; благодаря ему один chart можно поставить несколько раз без конфликтов имён. Пароль в `values.yaml` открытым текстом — временный компромисс; убираем его в шаге 14.6.

### why
Репетиция `helm template` — главный инструмент отладки: прежде чем что-то ломать в кластере, смотрим готовый YAML глазами. Если манифест некорректен, это видно здесь.

### deep Если не получилось
- **`lint` ругается на `templates/_helpers.tpl`** — файл остался от `helm create` и ссылается на значения, которых больше нет; для 12-й сессии его можно очистить: `: > charts/coffeeshop-api/templates/_helpers.tpl`.
- **`YAML parse error`** — проверь пробелы вокруг `{{ }}` и отступы; детали — шаг 12.7.

### quiz
- Что делает `helm template` и чем он безопаснее `install`?
- Зачем в имена объектов подставлен `.Release.Name`?
- Что делает `| quote`?

### links
- https://helm.sh/docs/chart_template_guide/values_files/ | значения | Helm: Values Files
- https://helm.sh/docs/helm/helm_template/ | helm template | Helm: helm template

## 12.6 install, upgrade, get | short: install и upgrade | est: ~40 мин
### intro
**Слова шага:** *`helm install`*, *`helm upgrade`*, *ревизия*, *`--set`*, *`helm get manifest`*.

:::tip Если совсем просто
`install` — первый заказ, `upgrade` — «то же, но с изменениями». Каждый заказ записывается в журнал под своим номером — ревизией. Если не нравится — открой журнал и верни прошлый.
:::

```bash run
cd ~/kubernetes-lab/charts
helm install demo coffeeshop-api --namespace helm-demo --create-namespace
kubectl rollout status deployment/demo-api -n helm-demo --timeout=90s
kubectl get pods,svc -n helm-demo
helm list -n helm-demo
```

### result
```out auto
```

Обрати внимание на имена: `demo-api` — потому что `{{ .Release.Name }}-api`. В списке релизов `REVISION 1`, `STATUS deployed`. Теперь обновим: больше реплик, и посмотрим, что изменилось:

```bash run
cd ~/kubernetes-lab/charts
helm upgrade demo coffeeshop-api -n helm-demo --set replicaCount=3
kubectl rollout status deployment/demo-api -n helm-demo --timeout=90s
helm list -n helm-demo
helm history demo -n helm-demo
helm get values demo -n helm-demo
helm get manifest demo -n helm-demo | grep -m1 'replicas:'
```

### result
```out auto
```

Ревизия стала `2`; `history` показывает обе, `get values` — что переопределено (`replicaCount: 3`), `get manifest` — реально применённый YAML. Важная ловушка: `helm upgrade` без `--reuse-values` или `-f` **сбрасывает** разовые `--set` предыдущего запуска к значениям chart’а. Поэтому в команде upgrade нужно каждый раз указывать полный набор значений — лучше файлом (`-f values-prod.yaml`, шаг 14.5), а не россыпью `--set`.

### why
Каждая ревизия — полный снимок: что было применено и с какими значениями. Это основа для `rollback` (шаг 14.3) и ответа на вопрос «что изменилось между вчера и сегодня».

### deep Команды по частям
`helm install <имя релиза> <chart> --namespace <ns> --create-namespace`: имя релиза уникально в namespace; `--create-namespace` создаёт namespace, если его нет. `helm upgrade --install <имя> <chart>` — «обнови, а если не установлен — установи»: именно эту форму ставят в скриптах и CI (шаг 14.3).

### deep Если не получилось
- **`Error: INSTALLATION FAILED: Unable to continue with install: … exists and cannot be imported`** — Helm не станет перехватывать объект, созданный не им (`kubectl apply`); поэтому мы ставим релиз в отдельный namespace `helm-demo`, а не поверх уже существующих объектов из `default`.
- **Pod’ы в `CrashLoopBackOff`** — API не находит БД. Это нормально для демо без неё, если `db.default.svc.cluster.local` недоступна; для проверки установки достаточно, что объекты созданы, а `rollout status` покажет реальное состояние.

### quiz
- Что произойдёт с `--set` из предыдущего запуска при следующем `helm upgrade`?
- Как посмотреть YAML, который Helm реально применил в кластере?
- Чем `helm upgrade --install` удобнее двух отдельных команд?

### links
- https://helm.sh/docs/helm/helm_upgrade/ | helm upgrade | Helm: helm upgrade
- https://helm.sh/docs/helm/helm_get_manifest/ | helm get manifest | Helm: helm get manifest

## 12.7 🔨 `helm install` падает: сломанный YAML | short: 🔨 Сломанный YAML | est: ~35 мин
### intro
**Слова шага:** *`YAML parse error`*, *ошибка шаблона*, *`--debug`*, *`helm template` как отладчик*.

:::tip Если совсем просто
Шаблон — это бланк с вырезанными окошками. Если окошко прорезано не там или в него подставили «не то», готовая бумага не читается. Сам бланк (шаблон) может быть «правильным» с точки зрения Helm, а результат — нечитаемым для Kubernetes. Диагноз ставят, глядя на готовую бумагу, а не на бланк.
:::

Сломаем шаблон: уберём пробел после двоеточия и укажем несуществующее значение.

```bash run
cd ~/kubernetes-lab/charts
cp coffeeshop-api/templates/service.yaml /tmp/service.yaml.bak
sed -i.bak 's/- port: {{ .Values.service.port }}/- port:{{ .Values.service.port }}/' coffeeshop-api/templates/service.yaml
helm lint coffeeshop-api 2>&1 | head -8
helm template demo coffeeshop-api 2>&1 | head -6
helm template demo coffeeshop-api --debug 2>&1 | grep -B2 -A6 'port:' | head -14
```

### result
```out auto
```

`helm lint` и `helm template` сообщают `YAML parse error` и номер строки **в готовом документе**, а `--debug` печатает весь результат подстановки, даже сломанный, — видно `- port:80` без пробела. Чиним:

```bash run
cd ~/kubernetes-lab/charts
cp /tmp/service.yaml.bak coffeeshop-api/templates/service.yaml
rm -f coffeeshop-api/templates/service.yaml.bak
helm lint coffeeshop-api
helm template demo coffeeshop-api >/dev/null && echo "шаблон снова собирается"
```

### result
```out auto
```

Теперь вторая ловушка: **значение, которого нет**.

```bash run
cd ~/kubernetes-lab/charts
helm template demo coffeeshop-api --set image.tag= | grep 'image:'
helm template demo coffeeshop-api --set image=oops 2>&1 | head -4
```

### result
```out auto
```

Пустой тег превращается в `coffeeshop-api:` — шаблон «правильный», а образ не скачается (`InvalidImageName`). Передача строки вместо словаря (`image=oops`) ломает шаблон `.Values.image.repository` («nil pointer»). Обе проблемы ловятся на этапе `template`, до кластера.

**Приёмка сессии:** API устанавливается chart’ом (`helm install demo …`), обновляется (`helm upgrade … --set replicaCount=3`), `helm lint` без ошибок, ревизии видны в `helm history`. Убираем:

```bash run
helm uninstall demo -n helm-demo
kubectl delete namespace helm-demo
```

### why
Порядок отладки Helm: `helm lint` (структура) → `helm template --debug` (результат подстановки) → `helm install --dry-run --debug` (проверка с кластером, но без применения) → только потом настоящая установка. Правило: **читай сгенерированный YAML, а не шаблон** — все ошибки видны там.

### deep Если не получилось
- **`sed -i.bak` не изменил файл** — на macOS нужна именно форма `sed -i.bak` (или `sed -i ''`); проверь `grep 'port:' coffeeshop-api/templates/service.yaml`.

### quiz
- Какая команда покажет итоговый YAML вместе с ошибкой?
- Почему шаблон может быть «валидным» для Helm и всё равно ломать установку?
- В каком порядке отлаживать chart?

### links
- https://helm.sh/docs/chart_template_guide/debugging/ | отладка шаблонов | Helm: Debugging Templates

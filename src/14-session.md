# Сессия 14 · Репозитории, релизы, окружения
dur: ~4 ч

## 14.1 Свой репозиторий chart’ов | short: Репозиторий chart’ов | est: ~35 мин
### intro
**Слова шага:** *`helm package`*, *`helm repo index`*, *`index.yaml`*, *репозиторий как статический сайт*.

:::tip Если совсем просто
Репозиторий chart’ов — это полка с запакованными рецептами и опись на ней (`index.yaml`). Никакой хитрой программы: любой сервер, который умеет отдавать файлы по HTTP, может быть репозиторием — лишь бы рядом с архивами лежала опись.
:::

```svg
@chart-repo
```

```bash run
cd ~/kubernetes-lab
mkdir -p repo
helm package charts/coffeeshop-api charts/coffeeshop-db --destination repo
helm repo index repo --url http://localhost:8879
ls repo
head -22 repo/index.yaml
```

### result
```out auto
```

`helm package` превращает папку chart’а в архив `имя-версия.tgz` (имя и версия берутся из `Chart.yaml` — поэтому при каждом изменении шаблонов **версию нужно повышать**, иначе в репозитории окажутся два разных chart’а с одним номером). `helm repo index` создаёт `index.yaml` — опись с именами, версиями, адресами архивов и контрольными суммами. Раздаём «полку»:

```bash run
cd ~/kubernetes-lab
(python3 -m http.server 8879 --directory repo >/dev/null 2>&1 &)
sleep 2
curl -s http://localhost:8879/index.yaml | head -5
```

### result
```out auto
```

В реальной жизни полка — это GitHub Pages, S3-совместимое хранилище, OCI-реестр (`helm push chart.tgz oci://…`) или ChartMuseum. OCI-реестр — сегодня самый распространённый способ: chart хранится как образ, рядом с Docker-образами. Принцип тот же: версионированный архив + доступ по HTTP(S).

### why
Репозиторий превращает «папку на моём ноутбуке» в общий источник: команда и CI ставят *одну и ту же* версию chart’а. Важное правило: **в репозиторий не кладут секреты** — `values.yaml` в архиве читает любой, кто имеет доступ к полке.

### deep Если не получилось
- **Порт 8879 занят** — выбери другой, и тот же номер укажи в `--url` и в `helm repo add`.
- **`python3: command not found`** — любой другой статический сервер подойдёт (`npx serve repo`, `caddy file-server --listen :8879 --root repo`).

### quiz
- Что находится в `index.yaml`?
- Почему при изменении шаблонов нужно повышать `version` в `Chart.yaml`?
- Почему нельзя класть секреты в chart из репозитория?

### links
- https://helm.sh/docs/topics/chart_repository/ | репозитории chart’ов | Helm: The Chart Repository Guide
- https://helm.sh/docs/topics/registries/ | OCI-реестры | Helm: Registries

## 14.2 repo add, search, установка из репозитория | short: Установка из репозитория | est: ~25 мин
### intro
**Слова шага:** *`helm repo add/update/list/search`*, *версия chart’а*, *`--version`*.

:::tip Если совсем просто
Теперь мы — читатель, а не автор: подключаем полку по адресу, обновляем опись и ставим рецепт по имени, как любой чужой chart (шаг 12.3).
:::

```bash run
helm repo add coffee http://localhost:8879
helm repo update coffee
helm repo list
helm search repo coffee/
helm show chart coffee/coffeeshop-api | head -8
```

### result
```out auto
```

`helm search repo coffee/` перечисляет chart’ы и версии из подключённого репозитория (`--versions` покажет все версии, а не только последнюю). Установка по имени — `helm install api coffee/coffeeshop-api --version 0.1.0`; `--version` закрепляет номер (без него берётся последняя, и повторяемость теряется).

### why
Закреплять версию chart’а — то же правило, что закреплять тег образа (шаг 9.6): без этого завтрашний `install` может принести другое приложение.

### quiz
- Зачем `helm repo update`?
- Что произойдёт при `helm install` без `--version`?

### links
- https://helm.sh/docs/helm/helm_repo/ | helm repo | Helm: helm repo

## 14.3 Жизненный цикл релиза | short: upgrade, rollback, atomic | est: ~50 мин
### intro
**Слова шага:** *`helm upgrade --install`*, *`helm history`*, *`helm rollback`*, *`--wait`*, *`--atomic`*, *`--timeout`*.

:::tip Если совсем просто
Релиз — это живое приложение с журналом изменений. `--wait` — «не говори, что готово, пока Pod не готовы», `--atomic` — «если не готовы вовремя, откати всё само, как было». Это страховочный трос при выкатке: плохая версия не остаётся в кластере наполовину.
:::

Поставим базу и API в namespace `shop-dev`, затем «выкатим» заведомо неработающую версию:

```bash run
kubectl create namespace shop-dev
helm upgrade --install db coffee/coffeeshop-db -n shop-dev --set auth.password=s3cret --wait --timeout 3m
helm upgrade --install api coffee/coffeeshop-api -n shop-dev --set db.password=s3cret --set db.host=db --wait --timeout 3m
helm history api -n shop-dev
echo "=== плохая выкатка с --atomic:"
helm upgrade api coffee/coffeeshop-api -n shop-dev --set db.password=s3cret --set db.host=db --set image.tag=no-such-tag --atomic --wait --timeout 60s 2>&1 | tail -3
helm history api -n shop-dev
kubectl get pods -n shop-dev
```

### result
```out auto
```

`helm upgrade --install` — одна команда для первой установки и всех обновлений (то, что кладут в скрипты и CI). Плохой тег образа приводит к `ImagePullBackOff`; Pod не становятся готовыми за 60 секунд; `--atomic` откатывает релиз сам, и `history` показывает ревизию `rolled back` — рабочие Pod’ы на месте, пользователи ничего не заметили (старые реплики никуда не уходили: помнишь `maxUnavailable` из шага 4.3).

Ручной откат и удаление:

```bash run
helm upgrade api coffee/coffeeshop-api -n shop-dev --set db.password=s3cret --set db.host=db --set replicaCount=3 --wait
helm history api -n shop-dev
helm rollback api 1 -n shop-dev --wait
helm history api -n shop-dev
kubectl get deploy api-api -n shop-dev
```

### result
```out auto
```

`helm rollback api 1` возвращает **содержимое** ревизии 1, но записывает его **новой ревизией** (журнал только растёт — история сохраняется). Число реплик снова из первой ревизии. `helm uninstall <имя>` убирает релиз; `--keep-history` оставляет журнал, чтобы потом его можно было откатить.

### why
`--atomic --wait --timeout` — три флага, которые в продакшне нужны почти всегда: без них `helm upgrade` рапортует «успех» сразу после отправки манифестов, хотя Pod ещё даже не стартовали. Откат одной командой при аварии (`helm rollback`) — главное, ради чего ценят релизы.

### deep Если не получилось
- **`Error: UPGRADE FAILED: timed out waiting for the condition`** без `--atomic` — релиз остаётся в статусе `failed`; чини значения и повторяй `upgrade`, либо `helm rollback`.
- **В Helm 4 флаг `--wait` по умолчанию «умнее»** (следит за готовностью через watcher); результат для нас тот же — команда ждёт готовности.

### quiz
- Что делает `--atomic`?
- Что именно записывает `helm rollback` — старую ревизию или новую?
- Почему `upgrade --install` удобен для CI?

### links
- https://helm.sh/docs/helm/helm_upgrade/#options | флаги upgrade | Helm: helm upgrade options
- https://helm.sh/docs/helm/helm_rollback/ | helm rollback | Helm: helm rollback

## 14.4 Проверки до выкатки: lint, dry-run, test, diff | short: Проверки | est: ~40 мин
### intro
**Слова шага:** *`helm lint`*, *`--dry-run`*, *`helm test`*, *`helm diff`*, *хук `helm.sh/hook: test`*.

:::tip Если совсем просто
Перед тем как нажать «выкатить», хочется три вещи: проверить, что бумаги составлены правильно (`lint`), прикинуть, что именно изменится (`diff`), и после — убедиться, что приложение отвечает (`test`).
:::

```bash run
cd ~/kubernetes-lab/charts
helm lint coffeeshop-api --set db.password=x --strict
helm upgrade api coffeeshop-api -n shop-dev --set db.password=s3cret --set db.host=db --set replicaCount=4 --dry-run=client 2>&1 | head -5
helm plugin install https://github.com/databus23/helm-diff 2>&1 | tail -2
helm diff upgrade api coffeeshop-api -n shop-dev --set db.password=s3cret --set db.host=db --set replicaCount=4 2>&1 | grep -E '^[+-] |replicas' | head
```

### result
```out auto
```

`--dry-run=client` считает шаблоны на стороне клиента, `--dry-run=server` дополнительно отправляет их в API-сервер на проверку (поймает то, что `lint` не видит: неизвестные поля, нарушение политик из шага 9.4) — второе надёжнее. `helm diff` (плагин) показывает построчно, что изменится в кластере по сравнению с установленным релизом: ровно то, что хочется увидеть в код-ревью. Если Helm отказывается ставить плагин без подписи, добавь `--verify=false` (в Helm 4 проверка подписи плагинов строже).

Добавим **тест-хук** — Pod, который проверяет работу релиза и завершается с кодом:

```bash run
cd ~/kubernetes-lab/charts
mkdir -p coffeeshop-api/templates/tests
cat > coffeeshop-api/templates/tests/test-connection.yaml <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: {{ include "coffeeshop-api.fullname" . }}-test
  annotations:
    "helm.sh/hook": test
    "helm.sh/hook-delete-policy": hook-succeeded
spec:
  restartPolicy: Never
  containers:
    - name: wget
      image: busybox:1.36
      command: ["wget", "-q", "-O-", "-T", "5", "http://{{ include "coffeeshop-api.fullname" . }}:{{ .Values.service.port }}{{ .Values.probes.path }}"]
EOF
helm upgrade api coffeeshop-api -n shop-dev --set db.password=s3cret --set db.host=db --wait --timeout 3m
helm test api -n shop-dev
```

### result
```out auto
```

`helm test` запускает все объекты с хуком `test`, ждёт завершения и сообщает `Phase: Succeeded` или `Failed`. Это «дымовой тест» релиза: подходит как последний шаг CI после `upgrade`.

### why
Три разных вопроса — три инструмента: «корректен ли chart?» (`lint --strict`), «что изменится?» (`diff`, `--dry-run=server`), «работает ли выкаченное?» (`test`). Вместе они делают выкатку предсказуемой.

### deep Если не получилось
- **`helm plugin install` не скачал** — нет доступа к GitHub; пропусти `diff`, остальное работает без плагина.
- **`helm test`: `Failed`** — `kubectl logs api-api-test -n shop-dev` (Pod, если не удалён политикой); частая причина — приложение отвечает ошибкой, потому что БД ещё не готова.

### quiz
- Чем `--dry-run=server` надёжнее `--dry-run=client`?
- Что показывает `helm diff`?
- Как Helm узнаёт, что Pod — это тест, а не часть приложения?

### links
- https://helm.sh/docs/topics/chart_tests/ | тесты chart’ов | Helm: Chart Tests
- https://github.com/databus23/helm-diff | helm-diff | GitHub: databus23/helm-diff

## 14.5 Окружения: values-dev и values-prod | short: Окружения | est: ~40 мин
### intro
**Слова шага:** *`-f values-*.yaml`*, *приоритет значений*, *`--set`*, *слияние словарей*.

:::tip Если совсем просто
Один рецепт торта — три размера порции. Базовые значения лежат в самом chart’е (`values.yaml`), а «размер» выбирается файлом: `values-dev.yaml` — маленькая порция, `values-prod.yaml` — большая. Выбранный файл переписывает только то, что в нём указано, остальное берётся из базового.
:::

Порядок приоритета значений Helm (позже — сильнее):

1. `values.yaml` внутри chart’а
2. файлы `-f` (чем правее в командной строке, тем сильнее)
3. `--set`, `--set-string`, `--set-file`

```bash run
mkdir -p ~/kubernetes-lab/envs && cd ~/kubernetes-lab/envs
cat > values-dev.yaml <<'EOF'
replicaCount: 1
resources:
  requests: {cpu: 50m, memory: 64Mi}
  limits: {memory: 128Mi}
ingress:
  enabled: false
EOF
cat > values-prod.yaml <<'EOF'
replicaCount: 3
resources:
  requests: {cpu: 100m, memory: 128Mi}
  limits: {memory: 256Mi}
ingress:
  enabled: true
  host: shop.localhost
EOF
kubectl create namespace shop-prod
export DB_PASSWORD=s3cret
helm upgrade --install db coffee/coffeeshop-db -n shop-prod --set auth.password="$DB_PASSWORD" --wait --timeout 3m
helm upgrade --install api coffee/coffeeshop-api -n shop-dev  -f values-dev.yaml  --set db.password="$DB_PASSWORD" --set db.host=db --wait --timeout 3m
helm upgrade --install api coffee/coffeeshop-api -n shop-prod -f values-prod.yaml --set db.password="$DB_PASSWORD" --set db.host=db --wait --timeout 3m
kubectl get deploy -n shop-dev  api-api -o custom-columns=NS:.metadata.namespace,REPLICAS:.spec.replicas,CPU:.spec.template.spec.containers[0].resources.requests.cpu
kubectl get deploy -n shop-prod api-api -o custom-columns=NS:.metadata.namespace,REPLICAS:.spec.replicas,CPU:.spec.template.spec.containers[0].resources.requests.cpu
kubectl get ingress -n shop-dev
kubectl get ingress -n shop-prod
helm get values api -n shop-prod
```

### result
```out auto
```

Разные ресурсы и реплики из разных файлов, Ingress — только в `prod`. `helm get values` показывает, что именно переопределено — удобно для аудита («чем прод отличается от дефолта»). Пароль передан через **переменную окружения** (`"$DB_PASSWORD"`), а не записан в файл, который попадёт в Git.

Проверим слияние: переопределим одно значение поверх файла:

```bash run
cd ~/kubernetes-lab/envs
helm template api coffee/coffeeshop-api -f values-prod.yaml --set replicaCount=5 --set db.password=x | grep 'replicas:'
```

### result
```out auto
```

`--set` сильнее файла (5 вместо 3). Файлы-окружения хранят в Git вместе с кодом; значения, которые отличаются *между* окружениями (число реплик, ресурсы, хост), лежат в файлах, а **секретные** — нигде в файлах (шаг 14.6).

### why
Структура «базовый `values.yaml` + маленький файл-окружение» — стандарт: в файле окружения только отличия, поэтому сразу видно, чем прод отличается от дев. Переход между окружениями — это смена `-f` и `-n`, а не правка шаблонов.

### deep Если не получилось
- **`Error: … not found: db` у API в `shop-dev`** — в `shop-dev` база уже установлена в шаге 14.3; если ты её удалила, поставь снова.
- **Список в values перезаписывается целиком, а не дополняется** — слияние идёт по словарям (ключ за ключом), а списки заменяются полностью.

### quiz
- Какой источник значений сильнее: `--set` или `-f`?
- Что хранится в файле `values-prod.yaml`, а что — нет?
- Как передать пароль, не записывая его в файл?

### links
- https://helm.sh/docs/chart_template_guide/values_files/#scope-dependencies-and-values | порядок значений | Helm: Values Files
- https://helm.sh/docs/helm/helm_install/#options | флаги install | Helm: install options

## 14.6 Секреты и Helm | short: Секреты в Helm | est: ~30 мин
### intro
**Слова шага:** *секреты вне Git*, *`existingSecret`*, *Sealed Secrets*, *`helm-secrets` + SOPS*, *External Secrets*.

:::tip Если совсем просто
Рецепт торта можно печатно раздавать всем; пароль от сейфа — нет. Поэтому chart и файлы окружений не содержат секретов: пароль «приходит» отдельным путём (из переменной, из шифрованного файла, из хранилища секретов).
:::

Что мы сделали до сих пор: пароль передан `--set db.password="$DB_PASSWORD"` из переменной окружения. Это работает, но Helm сохраняет **полные значения релиза** в Secret `sh.helm.release.v1.*` — посмотри сам:

```bash run
kubectl get secret -n shop-prod -l owner=helm -o name
kubectl get secret -n shop-prod -l owner=helm -o jsonpath='{.items[0].data.release}' | base64 -d | base64 -d | gunzip | grep -o '"password":"[^"]*"' | head -2
```

### result
```out auto
```

Пароль виден в данных релиза любому, у кого есть право читать Secret в этом namespace (RBAC из шага 9.1!). Поэтому в настоящих кластерах секреты **не передают через значения chart’а** вовсе. Варианты, от простого к надёжному:

| Способ | Идея |
|---|---|
| **`existingSecret`** | chart не создаёт Secret, а ссылается на уже существующий (`secretKeyRef` на имя из values); сам Secret создаёт другой процесс |
| **Sealed Secrets** | в Git лежит *зашифрованный* `SealedSecret`; расшифровать его может только контроллер в кластере |
| **helm-secrets + SOPS** | файл `secrets.yaml` в Git зашифрован ключом (age/KMS); Helm расшифровывает его при установке |
| **External Secrets Operator** | секрет живёт во внешнем хранилище (Vault, облачный менеджер секретов), оператор создаёт Secret в кластере |

Паттерн `existingSecret` в нашем chart’е — три строки: в `values.yaml` `db.existingSecret: ""`, в `secret.yaml` условие `{{- if not .Values.db.existingSecret }}` вокруг объекта, в `deployment.yaml` имя берётся из `{{ .Values.db.existingSecret | default (include "coffeeshop-api.fullname" .) }}`. В лабе этот паттерн оставлен для итогового задания (сессия 16): подумай, как ты его соберёшь.

### why
Правило: ни в `values.yaml`, ни в `values-*.yaml` в Git, ни в архивах репозитория не бывает ничего, чем можно воспользоваться. Секрет, однажды попавший в Git, считается скомпрометированным навсегда, даже если его удалили следующим коммитом.

### deep Если не получилось
- **Пустой вывод** второй команды — формат хранения зависит от версии Helm; смысл шага — не в команде, а в том, что значения релиза читаемы. Попробуй `helm get values api -n shop-prod --all` — тот же эффект.

### quiz
- Почему пароль, переданный через `--set`, всё равно виден в кластере?
- Чем Sealed Secrets отличается от обычного Secret?
- Какое значение в `values-prod.yaml` в Git можно хранить спокойно, а какое — нет?

### links
- https://helm.sh/docs/chart_best_practices/pods/#secrets | секреты | Helm: Best Practices — Secrets
- https://github.com/bitnami-labs/sealed-secrets | Sealed Secrets | GitHub: Sealed Secrets
- https://github.com/jkroepke/helm-secrets | helm-secrets | GitHub: helm-secrets

## 14.7 🔨 Релиз застрял в pending-upgrade | short: 🔨 pending-upgrade | est: ~35 мин
### intro
**Слова шага:** *статус релиза (`deployed`/`failed`/`pending-upgrade`)*, *блокировка релиза*, *`another operation is in progress`*.

:::tip Если совсем просто
Помощник пошёл переоформлять документы, оставил на двери табличку «Занято, идёт обновление» — и ушёл (его прервали). Дверь заперта навсегда: все следующие попытки войти получают «кто-то уже обновляет». Табличку нужно снять вручную.
:::

Прервём `helm upgrade` посреди работы (имитация закрытого ноутбука или упавшего CI-задания):

```bash run
cd ~/kubernetes-lab/envs
helm upgrade api coffee/coffeeshop-api -n shop-dev -f values-dev.yaml --set db.password=s3cret --set db.host=db --set replicaCount=2 --wait --timeout 5m &
HP=$!
sleep 3
kill -9 $HP
sleep 1
helm list -n shop-dev
echo "=== новая попытка:"
helm upgrade api coffee/coffeeshop-api -n shop-dev -f values-dev.yaml --set db.password=s3cret --set db.host=db 2>&1 | tail -2
helm history api -n shop-dev | tail -3
```

### result
```out auto
```

Статус релиза — `pending-upgrade`, новое обновление отказывается: `Error: UPGRADE FAILED: another operation (install/upgrade/rollback) is in progress`. Helm записал в журнал «обновление началось», но не успел записать «закончилось». Лечим откатом к последней рабочей ревизии:

```bash run
cd ~/kubernetes-lab/envs
helm rollback api -n shop-dev --wait
helm list -n shop-dev
helm upgrade api coffee/coffeeshop-api -n shop-dev -f values-dev.yaml --set db.password=s3cret --set db.host=db --wait --timeout 3m
helm history api -n shop-dev | tail -4
```

### result
```out auto
```

Если и `rollback` отказывается (бывает после повторных падений), крайняя мера — удалить Secret-запись зависшей ревизии: `kubectl delete secret sh.helm.release.v1.api.vN -n shop-dev`, где `N` — номер из `helm history` со статусом `pending-upgrade`. Это правка «журнала» руками — делай её, только поняв, что именно удаляешь.

**Приёмка сессии:** chart из своего репозитория установлен в `shop-dev` и `shop-prod` с разными значениями (`kubectl get deploy -n shop-dev,shop-prod`), переход между окружениями показан сменой файла значений, откат проверен.

Уборка:

```bash run
kill %% 2>/dev/null; pkill -f "http.server 8879" 2>/dev/null
helm uninstall api db -n shop-dev 2>/dev/null; helm uninstall api db -n shop-prod 2>/dev/null
kubectl delete namespace shop-dev shop-prod
helm repo remove coffee
```

### why
`pending-upgrade` — единственное «залипающее» состояние Helm, и оно почти всегда следствие прерывания (Ctrl+C, таймаут CI, закрытая крышка ноутбука). Поэтому в CI используют `--atomic` и `--timeout`, а прерывание обработки процессов считают штатной ситуацией, а не исключением.

### deep Если не получилось
- **`rollback` пишет `no revision for release`** — у релиза единственная ревизия (нечего откатывать): удали её через `helm uninstall --no-hooks` или запись Secret, затем поставь заново.

### quiz
- Почему после прерванного `upgrade` релиз застревает?
- Каким способом снять зависшее состояние в первую очередь?
- Какие флаги в CI защищают от такой ситуации?

### links
- https://helm.sh/docs/faq/troubleshooting/ | устранение проблем | Helm: Troubleshooting

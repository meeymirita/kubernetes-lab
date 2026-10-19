# Сессия 7 · Секреты и конфигурация
dur: ~4 ч

## 7.1 Зачем отделять конфиг от образа | short: 12-factor и конфиг | est: ~20 мин
### intro
**Слова шага:** *12-factor app*, *конфиг в окружении, не в коде*.

:::tip Если совсем просто
Один и тот же рецепт торта (образ) должен работать и для дня рождения на 10 человек, и на 100 — меняется не рецепт, а количество ингредиентов (конфиг: адрес базы, лимиты, флаги фич). Если зашить количество прямо в рецепт — для каждого случая нужен новый рецепт, то есть новый образ. Это именно то, чего мы избегаем.
:::

Принцип из методологии «12-factor app» (её ты уже видела в Laravel- и Docker-лабах): **конфигурация — это то, что меняется между окружениями (dev/staging/prod), а код — то, что не меняется.** Поэтому конфигурация никогда не должна быть зашита в образ — она приходит снаружи, во время запуска: переменными окружения, смонтированными файлами.

В Kubernetes для этого два типа объектов: **ConfigMap** — для несекретных настроек (адрес, таймауты, флаги), **Secret** — для чувствительных (пароли, токены, сертификаты), которые Kubernetes хранит и передаёт немного иначе (следующие шаги).

### result
Запускать здесь не будем — зафиксируем правило на всю сессию: **один и тот же образ `coffeeshop-api:v1` должен уметь работать и в dev, и в prod, меняя только то, что приходит ему через ConfigMap/Secret**, без пересборки.

### why
Этот принцип напрямую ведёт к Helm (сессия 12): `values-dev.yaml`/`values-prod.yaml` — это именно разные конфигурации для одного и того же chart'а/образа, не разные образы.

### quiz
- Что по 12-factor должно меняться между dev и prod — код или конфигурация?
- Зачем вообще два разных типа объектов (ConfigMap и Secret), если оба хранят пары «ключ-значение»?

### links
- https://12factor.net/ru/config | конфигурация в окружении | 12 Factor App: Config
- https://kubernetes.io/docs/concepts/configuration/overview/ | обзор конфигурации Kubernetes | Kubernetes: Configuration Best Practices

## 7.2 ConfigMap: из литералов и файлов | short: ConfigMap | est: ~40 мин
### intro
**Слова шага:** *ConfigMap*, *`envFrom`*, *монтирование как том*, *`subPath`*, *когда правка видна*.

:::tip Если совсем просто
ConfigMap — это записка на холодильнике с настройками кухни: «духовка разогрета до 180°, соль — по вкусу». Повар (контейнер) может прочитать её один раз при входе на смену (переменные окружения — читаются при старте) или подглядывать в неё периодически, если она лежит прямо на столе (смонтированный том — файл обновляется «на лету», но само приложение должно догадаться перечитать файл).
:::

```bash run
kubectl create configmap api-config \
  --from-literal=LOG_LEVEL=info \
  --from-literal=MENU_CACHE_TTL=60 \
  --dry-run=client -o yaml > manifests/06-configmap.yaml
cat manifests/06-configmap.yaml
kubectl apply -f manifests/06-configmap.yaml
```

### result
```out auto
```

Подключим его к Deployment API двумя способами одновременно — как переменные окружения и (для примера) как файл:

```bash run
kubectl patch deployment coffeeshop-api --type=strategic -p '
spec:
  template:
    spec:
      containers:
        - name: api
          envFrom:
            - configMapRef:
                name: api-config
'
kubectl rollout status deployment/coffeeshop-api
kubectl exec deploy/coffeeshop-api -- env | grep -E 'LOG_LEVEL|MENU_CACHE_TTL'
```

### result
```out auto
```

`envFrom.configMapRef` — все пары ConfigMap становятся переменными окружения **сразу**, без перечисления каждой по имени (альтернатива — `env[].valueFrom.configMapKeyRef` для одной конкретной переменной под своим именем).

**Когда правка видна приложению.** Переменные окружения читаются **один раз при старте контейнера** — правка ConfigMap **не** обновит их у уже запущенного Pod, нужен перезапуск (например, через `kubectl rollout restart deployment/...`). Если смонтировать ConfigMap как **том**, файл внутри контейнера обновится автоматически в течение примерно минуты (периодическая синхронизация `kubelet`) — но приложение должно само перечитывать файл, иначе разница не поможет.

### why
«Я поменяла ConfigMap, а приложение ничего не увидело» — почти всегда про способ подключения: через `env` нужен перезапуск, через том без перечитывания файла приложением — тоже ничего не изменится само. Понимание этой разницы экономит немало недоумения.

### deep subPath и другие варианты
`volumeMounts[].subPath` монтирует **один конкретный ключ** ConfigMap как отдельный файл по заданному пути (а не всю ConfigMap как каталог с файлами-по-ключам) — удобно, когда нужно подложить, например, один конфигурационный файл приложения в конкретное место, не трогая остальное содержимое каталога.

### deep Если не получилось
- **`envFrom` не подхватился** — проверь `kubectl rollout status`: `patch` запускает новый rollout, переменные появятся только в **новых** Pod, старые до завершения rollout их не видят (это и есть rolling update из сессии 4.3 в деле).

### quiz
- Почему правка ConfigMap не меняет переменные окружения у уже работающего Pod?
- Чем `envFrom` отличается от `env[].valueFrom.configMapKeyRef`?
- Для чего используется `subPath` при монтировании ConfigMap как тома?

### links
- https://kubernetes.io/docs/concepts/configuration/configmap/ | ConfigMap | Kubernetes: ConfigMap
- https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/ | использование ConfigMap в Pod | Kubernetes: Configure a Pod to Use a ConfigMap

## 7.3 Secret: типы, создание, подключение | short: Secret | est: ~40 мин
### intro
**Слова шага:** *Secret*, *`Opaque`*, *`kubernetes.io/dockerconfigjson`*, *`kubernetes.io/tls`*.

:::tip Если совсем просто
Если ConfigMap — рецепт на холодильнике, который может прочитать кто угодно на кухне, то Secret — **сейф с паролем от сейфа**, который кладут повару отдельно и который не вешают на видное место. Тип сейфа бывает разный: простой («любые ценности», `Opaque`), для ключей от чужого склада (`dockerconfigjson` — доступ к приватному registry), для сертификата (`tls`).
:::

```svg
@config-secret-delivery
```

```bash run
kubectl create secret generic db-credentials \
  --from-literal=POSTGRES_USER=coffeeshop \
  --from-literal=POSTGRES_PASSWORD='настоящий-пароль-не-этот'
kubectl get secret db-credentials -o yaml | head -10
```

### result
```out auto
```

Значения в выводе — **закодированы в base64**, не зашифрованы (следующий шаг объяснит разницу подробно). Подключим Secret к PostgreSQL вместо открытого пароля из шага 6.3:

```bash run
kubectl patch deployment db --type=strategic -p '
spec:
  template:
    spec:
      containers:
        - name: postgres
          env:
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef: {name: db-credentials, key: POSTGRES_USER}
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef: {name: db-credentials, key: POSTGRES_PASSWORD}
'
kubectl rollout status deployment/db
```

### result
```out auto
```

Три типа Secret, которые встретятся дальше: **`Opaque`** (по умолчанию, произвольные пары — наш случай), **`kubernetes.io/dockerconfigjson`** (учётные данные для скачивания образов из приватного registry — используется в `imagePullSecrets`, сессия 3.7), **`kubernetes.io/tls`** (сертификат + приватный ключ для HTTPS — пригодится, если понадобится TLS на Ingress, по аналогии с mkcert из Traefik-лабы).

### why
`secretKeyRef`/`configMapKeyRef` — то, что позволяет взять **одну конкретную** переменную под своим собственным именем, без заимствования всех ключей сразу (`envFrom`), что часто нужнее для чувствительных данных — явный список лучше неявного «всё, что там есть».

### deep Если не получилось
- **`kubectl create secret` показывает пароль в истории команд** — именно поэтому в реальных проектах значения берут из файла (`--from-file`) или переменной окружения терминала, а не вписывают прямо в команду; shell-история — не место для секретов (в этой лабе мы делаем это для простоты обучения, с пометкой «временный пароль»).

### quiz
- Чем `Opaque`-секрет отличается от `kubernetes.io/dockerconfigjson` по назначению?
- Как подключить одну конкретную переменную из Secret под своим именем?
- Почему вписывать реальный пароль прямо в команду в терминале — плохая привычка?

### links
- https://kubernetes.io/docs/concepts/configuration/secret/ | Secret | Kubernetes: Secret
- https://kubernetes.io/docs/concepts/configuration/secret/#secret-types | типы Secret | Kubernetes: Secret Types

## 7.4 Безопасность секретов: base64 ≠ шифрование | short: base64 ≠ шифрование | est: ~30 мин
### intro
**Слова шага:** *base64*, *шифрование etcd (encryption at rest)*, *RBAC на секреты*.

:::tip Если совсем просто
Base64 — это не замок, это просьба написать слово по-другому алфавиту: «пароль123» превращается в бессмысленный на вид набор символов, но **расшифровать** его обратно может любой, у кого есть пять секунд и доступ к `base64 -d` — никакого ключа не нужно. Это упаковка для безопасной передачи текста внутри YAML, а не защита содержимого.
:::

```bash run
echo 'coffeeshop' | base64
kubectl get secret db-credentials -o jsonpath='{.data.POSTGRES_USER}' | base64 -d
echo
```

### result
```out auto
```

Любой, у кого есть права на `kubectl get secret -o yaml` в этом namespace, **мгновенно** видит исходное значение. Настоящая защита строится из трёх слоёв:

1. **RBAC** (сессия 9.1) — ограничить, **кто** вообще может читать объекты `Secret` в этом namespace; это главный практический рубеж защиты.
2. **Шифрование `etcd` «на диске»** (*encryption at rest*) — без него Secret в самой базе `etcd` хранится в виде того же base64 (не зашифрован); включается на уровне control plane отдельной настройкой — в управляемых облачных кластерах обычно включено по умолчанию, в `kind` для учебных целей — нет (мы это не настраиваем, это конфигурация control plane, а не ресурс приложения).
3. **Внешние системы** (HashiCorp Vault, облачные Secret Manager + External Secrets Operator) — секрет вообще не хранится в Kubernetes постоянно, а запрашивается на лету; за пределами этой лабы, упомянуто для полноты картины.

### why
Путаница «Secret — это безопасно, потому что называется Secret» — опасная иллюзия у новичков. Название отражает **назначение** (хранить чувствительное) и чуть более аккуратную передачу (не попадает в `kubectl get pod -o yaml` напрямую, не светится в логах так легко, как ConfigMap), но не даёт автоматического шифрования без дополнительной настройки.

### deep Если не получилось
- **Хочется «просто зашифровать Secret»** — минимальный практический шаг в учебных целях — ограничить RBAC (сессия 9.1) на `get`/`list` секретов только тем ServiceAccount, которым это реально нужно; это куда важнее, чем настройка encryption at rest для стенда, который не содержит настоящих данных.

### quiz
- Что реально защищает base64-кодирование в Secret, а что — нет?
- Какие три слоя защиты секретов существуют и какой из них — главный практический рубеж?
- Почему encryption at rest для `etcd` не включена по умолчанию в учебном кластере `kind`?

### links
- https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/ | шифрование данных etcd | Kubernetes: Encrypting Confidential Data at Rest
- https://kubernetes.io/docs/concepts/configuration/secret/#information-security-for-secrets | безопасность Secret | Kubernetes: Information security for Secrets

## 7.5 Несколько сервисов: API ↔ БД ↔ Adminer | short: Весь стек вместе | est: ~35 мин
### intro
**Слова шага:** *сборка стека целиком*, *порядок применения манифестов*, *Adminer*.

:::tip Если совсем просто
До сих пор мы собирали CoffeeShop по кусочкам, как мебель из коробки — пора составить всё вместе в одной комнате и проверить, что диван не упирается в шкаф: API видит БД, фронтенд видит API, Adminer тоже видит БД.
:::

```bash run
cat > manifests/07-adminer.yaml <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: adminer
spec:
  replicas: 1
  selector: {matchLabels: {app: adminer}}
  template:
    metadata: {labels: {app: adminer}}
    spec:
      containers:
        - name: adminer
          image: adminer:latest
          ports: [{containerPort: 8080}]
---
apiVersion: v1
kind: Service
metadata: {name: adminer}
spec:
  selector: {app: adminer}
  ports: [{port: 80, targetPort: 8080}]
EOF
kubectl apply -f manifests/07-adminer.yaml
kubectl apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: adminer
  annotations: {kubernetes.io/ingress.class: traefik}
spec:
  ingressClassName: traefik
  rules:
    - host: adminer.shop.localhost
      http:
        paths:
          - {path: /, pathType: Prefix, backend: {service: {name: adminer, port: {number: 80}}}}
EOF
curl -s -o /dev/null -w 'adminer: HTTP %{http_code}\n' http://adminer.shop.localhost/
curl -s -o /dev/null -w 'api: HTTP %{http_code}\n' http://shop.localhost/api/health
curl -s -o /dev/null -w 'web: HTTP %{http_code}\n' http://shop.localhost/
```

### result
```out auto
```

Три адреса отвечают `200` — это тот самый результат, к которому вела Traefik-лаба, теперь полностью внутри Kubernetes: `shop.localhost` (frontend), `shop.localhost/api` (API → PostgreSQL через Secret), `adminer.shop.localhost` (прямой доступ к БД для отладки — тот же, что и в Compose).

### why
Собрать весь стек разом и проверить все адреса — лучшая проверка того, что labels/selector/ConfigMap/Secret совпадают везде, где должны. Если какой-то адрес не отвечает — это сигнал пройти по чеклисту предыдущих сессий (имена Service, selector, порты), а не начинать разбираться с нуля.

### deep Если не получилось
- **Adminer не может подключиться к БД** — ему нужно знать имя хоста (`db`, DNS-имя Service из сессии 5.3), пользователя и пароль — ты вводишь их в веб-форме Adminer при подключении, он не читает Secret автоматически (в отличие от API, который получает их через `env`).

### quiz
- Какие три адреса должны отвечать после сборки всего стека и за что отвечает каждый?
- Как Adminer получает учётные данные для подключения к БД — так же, как API, или иначе?

### links
- https://github.com/vrana/adminer | Adminer | GitHub: vrana/adminer

## 7.6 Отладка конфигурации и Ingress | short: Отладка целиком | est: ~25 мин
### intro
**Слова шага:** *порядок диагностики при сборке стека*, *частые опечатки*.

:::tip Если совсем просто
Когда «всё как-то не работает» после сборки нескольких частей — не паникуй и не переписывай всё заново: иди по списку сверху вниз, как механик по чеклисту перед полётом, а не как попытка угадать с десятой попытки.
:::

Общий порядок диагностики, который уже сложился из предыдущих сессий — соберём его в один список на эту сессию:

1. **Pod создан и `Running`?** (`kubectl get pods`) — если нет, смотри сессию 3 (образ) или сессию 8 (ресурсы, пробы).
2. **ConfigMap/Secret существуют и ключи совпадают буквально?** (`kubectl exec ... -- env`) — опечатка в имени ключа — самая частая причина `CreateContainerConfigError` (следующий 🔨-шаг).
3. **Service находит Pod?** (`kubectl get endpoints`) — несовпадение labels/selector (сессия 2.4, 3.4).
4. **Ingress находит Service?** (`kubectl describe ingress`) — опечатка в имени Service или порту (сессия 5.7).
5. **Приложение само отвечает на правильный путь?** — проверь `kubectl exec ... -- curl localhost:3000/health` **внутри** Pod, минуя Service и Ingress, чтобы изолировать, где именно проблема.

### result
Запускать не будем — это шаг-памятка, которую стоит приклеить (мысленно) на весь оставшийся курс: ровно тот же принцип «изолируй уровень», что был в Traefik-лабе (её собственная лесенка диагностики, сессия 10.4 там).

### why
Этот список экономит часы в сессиях 8–16, где ошибок становится больше, а стек — сложнее (Helm, автомасштабирование, безопасность). Привычка идти по уровням, а не хватаясь за первую догадку, — главный практический навык эксплуатации Kubernetes.

### quiz
- В каком порядке правильно проверять стек, если «что-то не работает», и почему именно в этом порядке?
- Как изолировать, работает ли само приложение, минуя Service и Ingress?

### links
- https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/ | отладка работающего Pod | Kubernetes: Debug Running Pods

## 7.7 🔨 CreateContainerConfigError: нет ключа в Secret | short: 🔨 CreateContainerConfigError | est: ~30 мин
### intro
**Слова шага:** *`CreateContainerConfigError`*, *несуществующий ключ Secret/ConfigMap*, *опечатка в имени*.

:::tip Если совсем просто
Это как попросить коллегу «передай мне пункт `D` из таблицы», а в таблице есть только `A`, `B`, `C` — коллега не может молча придумать значение, он обязан сказать «такого пункта нет». Kubernetes поступает так же: если `secretKeyRef`/`configMapKeyRef` ссылается на несуществующий ключ, контейнер **даже не пытается стартовать**.
:::

```bash run
kubectl patch deployment coffeeshop-api --type=json -p='[{"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"DB_PASSWORD","valueFrom":{"secretKeyRef":{"name":"db-credentials","key":"NO_SUCH_KEY"}}}}]'
sleep 8
kubectl get pods -l app=coffeeshop-api
newpod=$(kubectl get pods -l app=coffeeshop-api --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
kubectl describe pod "$newpod" | tail -8
```

### result
```out auto
```

Статус — **`CreateContainerConfigError`**, и это принципиально отличается от `CrashLoopBackOff` (сессия 4.7): контейнер **даже не запускался** — `kubelet` обнаружил, что не может собрать для него конфигурацию (переменную окружения не из чего взять), и отказался создавать контейнер вообще. В Events — явная причина: `couldn't find key NO_SUCH_KEY in Secret default/db-credentials`.

**Починка** — откатить `rollout`, как в шаге 4.4 (старые Pod не затронуты, так как это снова `RollingUpdate` с `maxUnavailable: 0`):

```bash run
kubectl rollout undo deployment/coffeeshop-api
kubectl rollout status deployment/coffeeshop-api
```

### result
```out auto
```

### why
`CreateContainerConfigError` — ещё одна строка в растущей таблице «статус → причина» (полная версия — сессия 8.6): он всегда про **конфигурацию**, которая не может быть собрана до старта контейнера (несуществующий ключ Secret/ConfigMap), и никогда не связан с самим кодом приложения — это разгружает голову при диагностике: не нужно даже заглядывать в логи приложения, оно не успело запуститься.

### deep Если не получилось
- **Статус другой, например `Pending`** — если это новый кластер без других Pod на этом месте, причина может быть в планировании, а не конфигурации; `describe` всегда скажет точно, какая это ситуация.

### quiz
- Чем `CreateContainerConfigError` отличается от `CrashLoopBackOff` по моменту, когда возникает проблема?
- Нужно ли смотреть логи приложения при `CreateContainerConfigError` и почему?
- Как убедиться, что откат не затронул уже работающие Pod?

### links
- https://kubernetes.io/docs/tasks/debug/debug-application/determine-reason-pod-failure/ | причины отказа Pod | Kubernetes: Determine the Reason for Pod Failure

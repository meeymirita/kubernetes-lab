# Сессия 9 · Безопасность и сеть-политики
dur: ~4 ч

## 9.1 RBAC: Role, RoleBinding, can-i | short: RBAC | est: ~40 мин
### intro
**Слова шага:** *RBAC*, *`Role`*, *`ClusterRole`*, *`RoleBinding`*, *`verb`*, *`kubectl auth can-i`*, *`--as`*.

:::tip Если совсем просто
RBAC — это пропускная система в офисе. `Role` — список дверей и что за ними можно делать («в переговорке — смотреть, в серверной — ничего»). `RoleBinding` — выдача бейджа конкретному человеку: «этому сотруднику — вот этот список». Пока бейдж не выдан, у человека нет ни одного права: в Kubernetes всё, что явно не разрешено, запрещено.
:::

```svg
@rbac-badge
```

Права в Kubernetes описываются тройкой: **кто** (user, group или `ServiceAccount`) — **что может делать** (`verbs`: `get`, `list`, `watch`, `create`, `update`, `delete`) — **с какими ресурсами** (`pods`, `secrets`, `deployments`…). `Role` и `RoleBinding` действуют **внутри одного namespace**, `ClusterRole` и `ClusterRoleBinding` — на весь кластер (или на cluster-scoped объекты вроде узлов).

Создадим роль «читатель Pod» в namespace `dev` (он остался с сессии 8.1) и выдадим её пользователю `jane`. Отдельного пользователя создавать не нужно: `kubectl auth can-i --as=jane` «притворяется» ею и спрашивает API-сервер, пустил бы он её.

```bash run
kubectl create role pod-reader -n dev --verb=get,list,watch --resource=pods
kubectl create rolebinding jane-pod-reader -n dev --role=pod-reader --user=jane
kubectl auth can-i list pods -n dev --as=jane
kubectl auth can-i delete pods -n dev --as=jane
kubectl auth can-i list pods -n default --as=jane
kubectl auth can-i list secrets -n dev --as=jane
```

### result
```out auto
```

Первая проверка — `yes`; остальные три — `no`: удалять нельзя (нет глагола `delete`), в другом namespace нельзя (`Role` не выходит за пределы `dev`), секреты нельзя (нет ресурса `secrets`). Полный список прав одного человека — `kubectl auth can-i --list --as=jane -n dev`.

### why
Принцип наименьших привилегий: каждому — ровно то, что нужно для работы. Привычка проверять права через `can-i --as` вместо «давайте дадим `cluster-admin`, чтобы заработало» отличает безопасный кластер от дырявого. Заодно `can-i` — быстрый способ понять, почему на другой машине выскакивает `forbidden`.

### deep Команды по частям
`kubectl create role pod-reader --verb=get,list,watch --resource=pods` — `--verb` и `--resource` можно повторять или перечислять через запятую. `--user=jane` в `rolebinding` — просто строка-имя: Kubernetes **не хранит** пользователей, их выдают сертификаты, токены или внешний провайдер входа; RBAC лишь сопоставляет имя из запроса с ролью. Готовый набор из коробки — `ClusterRole` `view` (только чтение почти всего), `edit`, `admin`, `cluster-admin`: `kubectl get clusterrole | grep -E '^(view|edit|admin|cluster-admin)'`.

### deep Если не получилось
- **`can-i` отвечает `yes` на всё подряд** — ты проверяешь от своего имени, а не `--as=jane`: у `kind` ты `cluster-admin`, и «админу можно всё».
- **`error: unknown flag: --as`** — флаг стоит после подкоманды `can-i` или в самом начале; ставь его в конец команды, как в примерах.

### quiz
- Чем `Role` отличается от `ClusterRole`?
- Что будет, если `Role` создана, а `RoleBinding` — нет?
- Как проверить, что `jane` может читать Pod в `dev`, не заходя в систему под её именем?

### links
- https://kubernetes.io/docs/reference/access-authn-authz/rbac/ | RBAC | Kubernetes: Using RBAC Authorization
- https://kubernetes.io/docs/reference/access-authn-authz/authorization/#checking-api-access | can-i | Kubernetes: Checking API Access

## 9.2 ServiceAccount: токен и доступ Pod к API | short: ServiceAccount | est: ~35 мин
### intro
**Слова шага:** *`ServiceAccount`*, *токен*, *`automountServiceAccountToken`*, *доступ из Pod к API-серверу*.

:::tip Если совсем просто
У людей бейджи выдаёт отдел кадров, а у программ внутри кластера — `ServiceAccount`. Это «бейдж для Pod»: Pod показывает его API-серверу, когда хочет что-то спросить («сколько у меня Pod?»). Без права на дверь Pod просто получит `403`, даже если он знает, где дверь.
:::

Каждый namespace уже содержит `ServiceAccount` `default`, и Pod без указания получает его. Создадим свой, выдадим ему чтение Pod и посмотрим на кластер глазами Pod:

```bash run
kubectl create serviceaccount coffee-reader -n dev
kubectl create rolebinding coffee-reader-binding -n dev --role=pod-reader --serviceaccount=dev:coffee-reader
kubectl apply -n dev -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: api-client}
spec:
  serviceAccountName: coffee-reader
  containers:
    - name: curl
      image: curlimages/curl
      command: ["sleep", "3600"]
EOF
kubectl wait -n dev --for=condition=Ready pod/api-client --timeout=60s
kubectl exec -n dev api-client -- sh -c '
SA=/var/run/secrets/kubernetes.io/serviceaccount
TOKEN=$(cat $SA/token)
echo "pods in dev:"; curl -s --cacert $SA/ca.crt -H "Authorization: Bearer $TOKEN" https://kubernetes.default.svc/api/v1/namespaces/dev/pods | grep -c "\"kind\": \"Pod\""
echo "secrets in dev:"; curl -s --cacert $SA/ca.crt -H "Authorization: Bearer $TOKEN" https://kubernetes.default.svc/api/v1/namespaces/dev/secrets | grep "\"reason\""
'
```

### result
```out auto
```

Список Pod получен, а на секреты пришёл ответ с `"reason": "Forbidden"`. Токен и корневой сертификат кластера Kubernetes сам положил в Pod по пути `/var/run/secrets/kubernetes.io/serviceaccount/` (проецируемый том): токен короткоживущий и обновляется автоматически, а адрес `kubernetes.default.svc` — это DNS-имя самого API-сервера внутри кластера (шаг 5.3).

### why
Большинство приложений **не должно** ходить в API Kubernetes вообще. Если приложению это не нужно, отключи токен: `automountServiceAccountToken: false` в `spec` Pod — тогда даже при взломе контейнера у злоумышленника нет бейджа. Операторам, контроллерам, Traefik (шаг 5.4) токен нужен — и им выдают узкие роли, а не `cluster-admin`.

### deep Токен вручную
`kubectl create token coffee-reader -n dev --duration=10m` выдаёт токен на 10 минут — полезно для скриптов и проверок снаружи. Раньше токены жили в вечных Secret’ах; начиная с 1.24 это не так, и вечный токен нужно создавать нарочно.

### deep Если не получилось
- **`curl: (60) SSL certificate problem`** — забыто `--cacert $SA/ca.crt`: кластер подписан собственным центром сертификации.
- **В ответе `Forbidden` и на Pod** — `RoleBinding` создан для другого namespace или имя сервис-аккаунта указано без префикса (`--serviceaccount=dev:coffee-reader`, формат `namespace:имя`).

### quiz
- Для чего нужен `ServiceAccount`, если у Pod нет «пользователя»?
- Где в контейнере лежит токен и кто его туда кладёт?
- Как отключить токен у Pod, которому он не нужен?

### links
- https://kubernetes.io/docs/concepts/security/service-accounts/ | ServiceAccount | Kubernetes: Service Accounts
- https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/ | настройка ServiceAccount | Kubernetes: Configure Service Accounts for Pods

## 9.3 securityContext: не root, неизменяемая файловая система | short: securityContext | est: ~40 мин
### intro
**Слова шага:** *`securityContext`*, *`runAsNonRoot`*, *`readOnlyRootFilesystem`*, *`allowPrivilegeEscalation`*, *`capabilities`*, *`seccompProfile`*.

:::tip Если совсем просто
Контейнер по умолчанию — сотрудник со связкой ключей «на всякий случай». `securityContext` — это отнять лишние ключи: работать не под администратором (`runAsNonRoot`), не позволять переписывать стены здания (`readOnlyRootFilesystem`), не разрешать «повышать себя до начальника» (`allowPrivilegeEscalation: false`) и отобрать особые полномочия Linux (`capabilities: drop: [ALL]`).
:::

Запустим два одинаковых Pod — без ограничений и с ними — и посмотрим на разницу:

```bash run
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: sec-open}
spec:
  containers:
    - name: c
      image: busybox:1.36
      command: ["sleep", "3600"]
---
apiVersion: v1
kind: Pod
metadata: {name: sec-locked}
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    seccompProfile: {type: RuntimeDefault}
  containers:
    - name: c
      image: busybox:1.36
      command: ["sleep", "3600"]
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities: {drop: ["ALL"]}
      volumeMounts:
        - {name: tmp, mountPath: /tmp}
  volumes:
    - {name: tmp, emptyDir: {}}
EOF
kubectl wait --for=condition=Ready pod/sec-open pod/sec-locked --timeout=60s
echo "--- open:";   kubectl exec sec-open   -- sh -c 'id -u; touch /etc/x && echo "запись в / разрешена"'
echo "--- locked:"; kubectl exec sec-locked -- sh -c 'id -u; touch /etc/x || echo "запись в / запрещена"; touch /tmp/ok && echo "запись в /tmp разрешена"'
kubectl delete pod sec-open sec-locked --now
```

### result
```out auto
```

В открытом Pod процесс работает под `uid 0` (root) и пишет куда угодно. В закрытом — под `10001`, корень файловой системы только для чтения, а писать можно лишь туда, где мы явно смонтировали `emptyDir` (`/tmp`). Если приложению нужна запись (кеш, временные файлы), даём ей **конкретный** каталог, а не разрешаем всё.

### why
Большая часть реальных взломов контейнеров — «вышли из приложения и оказались root с правом писать в систему». Каждое из четырёх ограничений закрывает отдельный путь. Хорошее правило: начинай с самых строгих настроек и ослабляй только то, что не работает, а не наоборот.

### deep Как применить к CoffeeShop API
Тот же блок `securityContext` добавляется в `Deployment` `coffeeshop-api` (в `spec.template.spec.containers[0]`). Если API пишет временные файлы, добавь `emptyDir` на `/tmp`. Образ API в `starter/` собран под непривилегированным пользователем `node`; проверить, под кем реально работает процесс: `kubectl exec deploy/coffeeshop-api -- id`. Образ, который *обязан* запускаться от root (например, `nginx` на порту 80), под `runAsNonRoot` не стартует — для таких есть варианты `nginxinc/nginx-unprivileged`.

### deep Если не получилось
- **`CreateContainerConfigError: container has runAsNonRoot and image will run as root`** — в образе нет явного пользователя; добавь `runAsUser` или смени образ. Это та же ошибка из шага 7.7, только причина другая: читай `describe`.
- **Приложение падает на «Read-only file system»** — оно пытается писать в корень; найди путь в логе и смонтируй туда `emptyDir`.

### quiz
- Чем `readOnlyRootFilesystem: true` помогает при взломе контейнера?
- Что делает `capabilities: drop: [ALL]`?
- Что делать, если приложению нужно писать временные файлы при `readOnlyRootFilesystem`?

### links
- https://kubernetes.io/docs/tasks/configure-pod-container/security-context/ | securityContext | Kubernetes: Configure a Security Context
- https://kubernetes.io/docs/concepts/security/linux-kernel-security-constraints/ | ограничения ядра Linux | Kubernetes: Linux kernel security constraints for Pods

## 9.4 Pod Security Standards: restricted на namespace | short: Pod Security Standards | est: ~35 мин
### intro
**Слова шага:** *Pod Security Standards*, *уровни `privileged`/`baseline`/`restricted`*, *метки `pod-security.kubernetes.io/*`*, *режимы `enforce`/`warn`/`audit`*.

:::tip Если совсем просто
В 9.3 мы вручную закрывали каждую «форточку» в каждом Pod — легко забыть. Pod Security Standards — это охранник на входе в целый namespace: «в это здание без пропуска `restricted` не входить». Вешается одной меткой на namespace, и Kubernetes сам отказывает в создании Pod, нарушающих правила.
:::

Три уровня: `privileged` (без ограничений, для системных компонентов), `baseline` (запрещает самое опасное), `restricted` (строгие современные практики: не root, без повышения привилегий, `seccomp`, `drop ALL`). Три режима: `enforce` — отказывать, `warn` — пускать, но предупреждать, `audit` — писать в журнал.

```bash run
kubectl create namespace secure-demo
kubectl label namespace secure-demo pod-security.kubernetes.io/enforce=restricted
echo "--- обычный nginx:"
kubectl run plain --image=nginx:alpine -n secure-demo 2>&1 | head -4
echo "--- соответствующий требованиям Pod:"
kubectl apply -n secure-demo -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: {name: compliant}
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    seccompProfile: {type: RuntimeDefault}
  containers:
    - name: c
      image: busybox:1.36
      command: ["sleep", "3600"]
      securityContext:
        allowPrivilegeEscalation: false
        capabilities: {drop: ["ALL"]}
EOF
kubectl get pods -n secure-demo
```

### result
```out auto
```

Первый Pod отвергнут с перечнем причин (`allowPrivilegeEscalation != false`, `unrestricted capabilities`, `runAsNonRoot != true`, `seccompProfile`), второй — принят. Обрати внимание: отказ приходит **сразу при создании**, а не «Pod создан и потом упал» — валидацию делает API-сервер. Но готовый `Deployment` создаётся успешно, а отказывают его **Pod’ам**: ошибка видна в `kubectl describe replicaset`, а не в `describe deployment` — частая путаница.

### why
Метка на namespace гарантирует, что **новые** рабочие нагрузки соответствуют стандарту, даже если автор манифеста про `securityContext` не знал. Безопасный путь внедрения в живой кластер: сначала `warn` и `audit`, посмотреть, что бы сломалось, исправить манифесты и лишь потом включать `enforce`.

### deep Если не получилось
- **Pod из Deployment не создаётся, а сам Deployment выглядит нормально** — открой события набора реплик: `kubectl describe rs -n <ns>` или `kubectl get events -n <ns>`; сообщение `violates PodSecurity "restricted:latest"` лежит там.
- **Нужно проверить заранее, не создавая:** `kubectl label --dry-run=server --overwrite ns <имя> pod-security.kubernetes.io/enforce=restricted` покажет предупреждения для существующих Pod namespace.

### quiz
- Чем режим `warn` отличается от `enforce`?
- Почему ошибка о нарушении стандарта видна в событиях ReplicaSet, а не Deployment?
- Какой уровень выбрать для namespace с обычным веб-приложением?

### links
- https://kubernetes.io/docs/concepts/security/pod-security-standards/ | Pod Security Standards | Kubernetes: Pod Security Standards
- https://kubernetes.io/docs/tasks/configure-pod-container/enforce-standards-namespace-labels/ | метки namespace | Kubernetes: Enforce Pod Security Standards with Namespace Labels

## 9.5 NetworkPolicy: «запретить всё» и разрешить нужное | short: NetworkPolicy | est: ~50 мин
### intro
**Слова шага:** *`NetworkPolicy`*, *default deny*, *`podSelector`*, *`ingress`/`egress`*, *CNI*.

:::tip Если совсем просто
По умолчанию в кластере любой Pod может заговорить с любым — как в офисе без внутренних дверей: бухгалтер может зайти в серверную. `NetworkPolicy` — это внутренние двери: сначала запираем всё («запретить весь входящий трафик к БД»), затем выдаём ключи только тем, кому нужно («пускать только API»).
:::

```svg
@netpol-doors
```

Правила `NetworkPolicy` пишутся в Kubernetes, но **выполняет их не он, а сетевой плагин (CNI)**. Если плагин политики не поддерживает, объект создастся без единой ошибки и… ничего не будет блокировать. Поэтому действуем так: создаём трёхзвенный стенд, применяем «запретить всё» и **сначала проверяем, что оно действительно запрещает**.

```bash run
kubectl create namespace shop-np
kubectl apply -n shop-np -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata: {name: db}
spec:
  replicas: 1
  selector: {matchLabels: {app: db}}
  template:
    metadata: {labels: {app: db}}
    spec:
      containers: [{name: db, image: nginx:alpine, ports: [{containerPort: 80}]}]
---
apiVersion: v1
kind: Service
metadata: {name: db}
spec:
  selector: {app: db}
  ports: [{port: 80}]
---
apiVersion: v1
kind: Pod
metadata: {name: api, labels: {app: api}}
spec:
  containers: [{name: c, image: busybox:1.36, command: ["sleep", "3600"]}]
---
apiVersion: v1
kind: Pod
metadata: {name: web, labels: {app: web}}
spec:
  containers: [{name: c, image: busybox:1.36, command: ["sleep", "3600"]}]
EOF
kubectl wait -n shop-np --for=condition=Ready pod --all --timeout=90s
echo "--- до политики:"
kubectl exec -n shop-np api -- wget -qO- -T 3 http://db | head -1
kubectl exec -n shop-np web -- wget -qO- -T 3 http://db | head -1
```

### result
```out auto
```

Обе команды получают страницу — ограничений пока нет. Теперь «запретить всё» для БД и отдельное разрешение для API:

```bash run
kubectl apply -n shop-np -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: {name: db-deny-all}
spec:
  podSelector: {matchLabels: {app: db}}
  policyTypes: [Ingress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: {name: db-allow-api}
spec:
  podSelector: {matchLabels: {app: db}}
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector: {matchLabels: {app: api}}
      ports:
        - {port: 80}
EOF
echo "--- после политики, api:"
kubectl exec -n shop-np api -- wget -qO- -T 3 http://db | head -1
echo "--- после политики, web:"
kubectl exec -n shop-np web -- wget -qO- -T 3 http://db | head -1 || echo "web: таймаут (заблокировано)"
```

### result
```out auto
```

Правильный результат: `api` получает страницу, `web` — таймаут (`wget: download timed out`). Первая политика (`db-deny-all`) — пустой список `ingress`, то есть «никому»; вторая **добавляет** разрешение для Pod с меткой `app=api` на порт 80. Политики складываются (объединение разрешений), а не заменяют друг друга.

### why
В этом шаге главное — привычка **проверять**, что политика реально работает, а не верить `kubectl get netpol`. Поэтому сначала шли команды «до», потом «после». Если `web` всё равно достучался — ваш CNI не применяет политики (см. «Если не получилось»), и написанные правила создают лишь **ложное чувство безопасности**.

### deep Если не получилось
- **`web` получает страницу и после политик** — CNI не поддерживает `NetworkPolicy`. Это зависит от версии плагина `kindnet` в вашем `kind`: в старых версиях политик не было. Решение — кластер с `Calico`: в `kind-config.yaml` указываешь `networking: {disableDefaultCNI: true, podSubnet: 192.168.0.0/16}`, создаёшь кластер (узлы будут `NotReady`, пока нет сети), затем ставишь оператор и ресурсы `Calico` v3.31.4 из документации проекта (`kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.31.4/manifests/tigera-operator.yaml`, затем `custom-resources.yaml` оттуда же) и ждёшь `kubectl get pods -n calico-system`. Переустановка кластера сотрёт текущий стенд — делай это в **отдельном** кластере (`kind create cluster --name netpol --config …`).
- **Нужно ограничить и исходящий трафик** — добавь `Egress` в `policyTypes` и правила `egress`. Не забудь разрешить DNS (порт 53 к `kube-dns` в `kube-system`), иначе имена перестанут разрешаться.

### quiz
- Кто на самом деле применяет правила `NetworkPolicy` — API-сервер или CNI?
- Что произойдёт, если создать `NetworkPolicy` в кластере, где CNI её не поддерживает?
- Почему политики `db-deny-all` и `db-allow-api` не конфликтуют, а работают вместе?

### links
- https://kubernetes.io/docs/concepts/services-networking/network-policies/ | NetworkPolicy | Kubernetes: Network Policies
- https://docs.tigera.io/calico/latest/getting-started/kubernetes/kind | Calico в kind | Calico: Install on kind

## 9.6 Образы и цепочка поставки: обзор | short: Цепочка поставки | est: ~25 мин
### intro
**Слова шага:** *digest образа*, *тег `latest`*, *подпись образа*, *сканирование уязвимостей*, *SBOM*.

:::tip Если совсем просто
Тег образа (`postgres:18`) — как надпись «молоко» на пакете: завтра в пакете может оказаться другое. Digest (`@sha256:…`) — серийный номер именно этой упаковки: он меняется, если изменить хоть один байт. Подпись — печать производителя, сканер — санитарный инспектор, который ищет в составе известные «просрочки».
:::

В этом шаге устанавливать ничего не нужно — это обзор того, что стоит делать, когда лабораторный кластер превращается в настоящий. Посмотрим, чем реальный Pod отличается от тега в манифесте:

```bash run
kubectl get pod -n kube-system -l component=kube-apiserver -o jsonpath='{.items[0].spec.containers[0].image}{"\n"}{.items[0].status.containerStatuses[0].imageID}{"\n"}'
```

### result
```out auto
```

Вторая строка — `imageID` с `sha256:…`: именно этот неизменяемый образ запущен на узле. Практика для настоящего кластера:

- **Не использовать `latest`** (мы использовали `adminer:latest` для учёбы): неизвестно, что запустится завтра. Закреплять конкретный тег, а лучше `image: имя@sha256:…`.
- **Сканировать образы** (`trivy image coffeeshop-api:v1` или сканер в реестре) на известные уязвимости до того, как образ попал в кластер.
- **Подписывать образы и проверять подпись** (проект `cosign` из Sigstore + политика приёма, например Kyverno или Ratify): в кластер входят только образы вашей сборки.
- **Хранить список состава** (SBOM): когда выйдет новая уязвимость, видно, какие образы затронуты.
- **Минимальные базовые образы** (`-slim`, `distroless`): чем меньше внутри, тем меньше атаковать.

### why
Все предыдущие шаги защищают *кластер от контейнера*. Цепочка поставки защищает *от того, что в контейнер попало ещё до запуска*. Эти меры подключают в CI/CD, а не в самом Kubernetes; поэтому здесь — обзор, а не упражнение.

### quiz
- Чем digest образа надёжнее тега?
- Почему тег `latest` — плохая идея для продакшна?
- На каком этапе (в кластере или до него) лучше сканировать образы и почему?

### links
- https://kubernetes.io/docs/concepts/containers/images/#image-names | имена образов | Kubernetes: Images
- https://docs.sigstore.dev/cosign/signing/overview/ | подпись образов | Sigstore: Cosign
- https://trivy.dev/latest/ | сканер Trivy | Trivy

## 9.7 🔨 Политика есть, а не работает | short: 🔨 Политика не работает | est: ~35 мин
### intro
**Слова шага:** *политика, выбирающая «пустое множество»*, *проверка `podSelector`*, *`kubectl describe networkpolicy`*.

:::tip Если совсем просто
Поставили на дверь серверной красивый замок и повесили табличку — но по ошибке не на ту дверь. Табличка есть, замок есть, а в серверную по-прежнему ходят все. Самая частая причина «NetworkPolicy не работает» — не CNI, а то, что политика **ни к одному Pod не применилась**: ярлык написан с опечаткой.
:::

Сломаем: заменим `db-deny-all` на политику с опечаткой в селекторе и убедимся, что `web` снова проходит.

```bash run
kubectl apply -n shop-np -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: {name: db-deny-all}
spec:
  podSelector: {matchLabels: {app: dbb}}
  policyTypes: [Ingress]
EOF
kubectl delete networkpolicy db-allow-api -n shop-np
echo "--- web после «политики»:"
kubectl exec -n shop-np web -- wget -qO- -T 3 http://db | head -1
echo "--- какие Pod выбирает политика:"
kubectl get pods -n shop-np -l app=dbb
kubectl describe networkpolicy db-deny-all -n shop-np | head -12
```

### result
```out auto
```

`web` снова получает страницу. Подсказки две: `kubectl get pods -l app=dbb` — «No resources found» (политика выбирает **пустое множество** Pod), а в `describe` видно `PodSelector: app=dbb`. Исправляем и возвращаем разрешение для API:

```bash run
kubectl apply -n shop-np -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: {name: db-deny-all}
spec:
  podSelector: {matchLabels: {app: db}}
  policyTypes: [Ingress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: {name: db-allow-api}
spec:
  podSelector: {matchLabels: {app: db}}
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector: {matchLabels: {app: api}}
      ports: [{port: 80}]
EOF
echo "api:"; kubectl exec -n shop-np api -- wget -qO- -T 3 http://db | head -1
echo "web:"; kubectl exec -n shop-np web -- wget -qO- -T 3 http://db | head -1 || echo "таймаут: заблокировано"
```

### result
```out auto
```

**Приёмка сессии:** `api` достучался до БД, `web` — нет; проверено командой `wget` из самого Pod, а не по виду `kubectl get netpol`. Убираем за собой:

```bash run
kubectl delete namespace shop-np secure-demo
kubectl delete pod api-client -n dev
```

### why
Правило проверки: после любой `NetworkPolicy` ищи два вопроса. «Выбрала ли она хоть один Pod?» (`get pods -l …` с её селектором) и «Применяет ли политики сетевой плагин?». Если ответ на оба «да», а трафик идёт — смотри следующий слой: нет ли *другой* политики, разрешающей этот поток (разрешения складываются).

### deep Если не получилось
- **Политика верная, `web` проходит** — вернись к шагу 9.5 «Если не получилось»: ваш CNI не применяет политики.
- **Всё заблокировано, даже `api`** — проверь `namespaceSelector`/`podSelector` в `from`: они находятся в **одном** элементе списка (логическое «и») или в **разных** (логическое «или») — отступ решает.

### quiz
- Как быстро проверить, что `NetworkPolicy` выбрала хотя бы один Pod?
- Какая разница между двумя селекторами в одном элементе `from` и в двух?
- Какие две причины у поведения «политика есть, а трафик не блокируется»?

### links
- https://kubernetes.io/docs/concepts/services-networking/network-policies/#behavior-of-to-and-from-selectors | to/from селекторы | Kubernetes: Behavior of to and from selectors

# Сессия 3 · Pod и Service
dur: ~4 ч

## 3.1 Pod: общая квартира контейнеров | short: Что такое Pod | est: ~30 мин
### intro
**Слова шага:** *Pod*, *контейнер в Pod*, *общая сеть и IP*, *общие тома*, *`restartPolicy`*.

:::tip Если совсем просто
Pod — это **общая квартира** для одного или нескольких контейнеров: у квартиры один почтовый адрес (IP), и все жильцы (контейнеры) видят друг друга через `localhost`, как соседи по комнатам одной квартиры видят общую прихожую. Чаще всего в квартире живёт один жилец — это нормально и даже типично: Pod — минимальная единица, а не обязательно «многоквартирный дом».
:::

**Pod** — наименьший объект, который реально разворачивается на узле. Важное свойство: все контейнеры внутри одного Pod **делят**:

- **сетевой namespace** — один IP-адрес на весь Pod; контейнеры внутри обращаются друг к другу через `localhost` и разные порты (как два процесса на одной машине);
- **тома** (при желании) — можно смонтировать общий каталог, который видят все контейнеры Pod;
- **жизненный цикл** — Pod создаётся и удаляется как единое целое; если ты пересоздаёшь Pod, пересоздаются все его контейнеры.

Простейший манифест:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: coffeeshop-api
  labels:
    app: coffeeshop-api
spec:
  containers:
    - name: api
      image: coffeeshop-api:v1
      ports:
        - containerPort: 3000
  restartPolicy: Always
```

`restartPolicy` относится ко **всем** контейнерам Pod: `Always` (по умолчанию для Deployment — перезапускать при любом завершении), `OnFailure` (только при ошибке — для Job, сессия 8), `Never` (разово — для диагностических Pod).

### result
Файл выше пока не применяем — применим в следующем шаге, когда разберём, что означает `restartPolicy` на практике с реальным статусом. Запомни главное: **Pod — это не «контейнер», это «квартира», в которой почти всегда живёт один контейнер**, но сам Kubernetes всегда работает именно с Pod, а не напрямую с контейнерами.

### why
Путаница «Pod = контейнер» — самая частая у новичков из Docker. Она ломается в первый раз, когда нужно несколько контейнеров с общей сетью (например, основной контейнер + «сайдкар» для логов) — Docker Compose решает это отдельными контейнерами в одной сети Compose, Kubernetes — одним Pod с несколькими контейнерами.

### deep Когда в одном Pod несколько контейнеров
Классический паттерн — **sidecar**: основной контейнер (приложение) + вспомогательный (например, отправка логов, обновление сертификата, прокси). Они всегда планируются **на один узел** и живут **одновременно** — в этой лабе мы такого не делаем (CoffeeShop — простые однопроцессные сервисы), но важно знать паттерн на будущее и для собеседований.

### deep Если не получилось понять разницу с Docker Compose
В Compose у тебя могут быть пять сервисов (контейнеров) в одной сети — в Kubernetes то же самое чаще всего превращается в **пять отдельных Pod** (по одному на сервис), а не один Pod с пятью контейнерами. Один Pod на несколько контейнеров — это именно для случаев, когда они обязаны жить и масштабироваться вместе, не по отдельности.

### quiz
- Что контейнеры внутри одного Pod делят между собой?
- В каком случае у Pod бывает больше одного контейнера и как это называется?
- Чем Pod отличается от того, что ты называла «сервисом» в Docker Compose?

### links
- https://kubernetes.io/docs/concepts/workloads/pods/ | что такое Pod | Kubernetes: Pods
- https://kubernetes.io/docs/concepts/workloads/pods/#pods-in-a-cluster | Pod в кластере | Kubernetes: Pods in a Cluster

## 3.2 Жизненный цикл Pod: Pending → Running | short: Фазы Pod | est: ~30 мин
### intro
**Слова шага:** *фаза Pod*, *`Pending`*, *`Running`*, *`Succeeded`*, *`Failed`*, *`Unknown`*.

:::tip Если совсем просто
Фаза Pod — это как статус посылки у курьерской службы: «принята» (Pending — ещё не доставлена, может, ждёт сортировки), «в пути и доставлена» (Running), «доставлена и всё, больше не едет» (Succeeded — для одноразовых задач), «потерялась» (Failed). Статус один на весь Pod, даже если контейнеров внутри несколько.

:::

Применим Pod из прошлого шага и понаблюдаем за фазами:

```bash run
cd ~/kubernetes-lab
kubectl apply -f manifests/00-demo-pod.yaml 2>/dev/null
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: coffeeshop-api
  labels:
    app: coffeeshop-api
spec:
  containers:
    - name: api
      image: coffeeshop-api:v1
      ports:
        - containerPort: 3000
EOF
kubectl get pod coffeeshop-api -w &
sleep 8
kill %1 2>/dev/null
```

### result
```out auto
```

Фазы, которые ты увидишь по порядку: **`Pending`** (манифест принят, но Pod ещё не запланирован на узел или образ ещё качается — это нормально, несколько секунд), затем **`Running`** (хотя бы один контейнер стартовал; если в Pod несколько контейнеров — `Running` означает, что все они запущены, но не обязательно `Ready`, это разные вещи, см. пробы в сессии 8). Для одноразовых задач (сессия 8, Job) финальная фаза — **`Succeeded`** (все контейнеры завершились с кодом 0) или **`Failed`** (хотя бы один завершился с ошибкой и больше не перезапускается).

**`Unknown`** — отдельный случай: control-plane потерял связь с узлом (например, `kubelet` не отвечает) и не знает, что там на самом деле происходит.

### why
Фаза — это **грубый** индикатор, не диагноз. `Running` не значит «работает правильно» — только что процесс стартовал. За настоящим здоровьем следят пробы готовности (сессия 8.2), а за причиной застревания в `Pending` — `kubectl describe` (следующий шаг).

### deep Pending дольше, чем ожидалось — куда смотреть
Если Pod висит в `Pending` дольше пары секунд: `kubectl describe pod <имя>` → раздел Events почти всегда называет причину буквально («Insufficient cpu», «0/3 nodes are available: node(s) had untolerated taint», «ImagePullBackOff» — следующие шаги разберут несколько таких причин подробно).

### deep Если не получилось
- **Фаза навечно `Pending`, Events молчат** — redo `kubectl get events --sort-by=.lastTimestamp` на весь namespace; иногда событие относится не к Pod, а к ReplicaSet/Deployment, который его создал (сессия 4).

### quiz
- Какие пять фаз у Pod и что отличает `Succeeded` от `Failed`?
- Что значит фаза `Running` и чего она **не** гарантирует?
- Когда Pod переходит в фазу `Unknown`?

### links
- https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/ | жизненный цикл Pod | Kubernetes: Pod Lifecycle

## 3.3 logs, exec, describe, события | short: logs и exec | est: ~35 мин
### intro
**Слова шага:** *`kubectl logs`*, *`kubectl exec`*, *несколько контейнеров в одном Pod*, *события (Events)*.

:::tip Если совсем просто
`kubectl logs` — подслушать, что контейнер **говорит сам** (его стандартный вывод). `kubectl exec` — зайти внутрь и **посмотреть своими глазами** (выполнить команду прямо в его файловой системе). Разные инструменты для разных вопросов: «что он сказал» и «что там внутри на самом деле».
:::

```bash run
kubectl logs coffeeshop-api --tail=20
kubectl exec -it coffeeshop-api -- sh -c "whoami && ls /app && cat /etc/hostname"
```

### result
```out auto
```

`kubectl logs` по умолчанию показывает вывод **первого** (или единственного) контейнера Pod; если контейнеров несколько — обязателен флаг `-c <имя-контейнера>`, иначе `kubectl` попросит его указать. `kubectl exec -it` открывает интерактивную сессию внутри контейнера (`-i` — интерактивный ввод, `-t` — псевдотерминал) — это именно то, что было у `docker exec -it`, только адресовано через Kubernetes API, а не прямо Docker-демону.

Полезные варианты:

```bash run
kubectl logs coffeeshop-api --previous 2>&1 | tail -5
kubectl get events --field-selector involvedObject.name=coffeeshop-api --sort-by=.lastTimestamp
```

### result
```out auto
```

`--previous` — журнал **предыдущего** запуска контейнера (если он перезапускался) — критично при `CrashLoopBackOff` (сессия 8): текущий запуск мог не успеть ничего написать, а предыдущий — успел упасть с понятной ошибкой. `kubectl get events --field-selector involvedObject.name=...` — та же хронология, что в конце `describe`, но отдельно и для конкретного имени.

### why
«Логи пустые» часто означает не «приложение молчит», а «ты смотришь логи **нового** контейнера после перезапуска, а не упавшего старого» — вот для чего `--previous`. Привыкай проверять оба варианта, прежде чем делать вывод «логов нет».

### deep Если контейнеров несколько
`kubectl logs <pod> --all-containers=true --prefix` — все контейнеры сразу, с префиксом имени перед каждой строкой; `kubectl exec <pod> -c <контейнер> -- ...` — выбрать конкретный для `exec`.

### deep Если не получилось
- **`error: unable to upgrade connection: container not found`** — опечатка в имени контейнера (не Pod); `kubectl get pod <имя> -o jsonpath='{.spec.containers[*].name}'` покажет точные имена.
- **`exec` работает, а `sh: not found`** — образ минимальный (`scratch`/`distroless`) и вообще не содержит шелла; тогда диагностика только через логи и `kubectl debug` (сессия 8.6).

### quiz
- Чем `kubectl logs` отличается от `kubectl exec` по тому, что они показывают?
- Когда полезен флаг `--previous` у `kubectl logs`?
- Что нужно указать дополнительно, если в Pod несколько контейнеров?

### links
- https://kubernetes.io/docs/reference/kubectl/generated/kubectl_logs/ | справочник kubectl logs | Kubernetes: kubectl logs
- https://kubernetes.io/docs/tasks/debug/debug-application/get-shell-running-container/ | shell в контейнере | Kubernetes: Get a Shell to a Running Container

## 3.4 Service: стабильный адрес для смертных Pod | short: Зачем Service | est: ~40 мин
### intro
**Слова шага:** *Service*, *`ClusterIP`*, *`selector`*, *`port`/`targetPort`*, *endpoint*.

:::tip Если совсем просто
Pod — номера в гостинице: они освобождаются, занимаются другими гостями, у каждого свой номер комнаты, который меняется при переезде. Service — стойка регистрации: её адрес **никогда не меняется**, и если ты звонишь на стойку и просишь «соедините с отделом бронирования», тебя соединят с тем, кто сейчас дежурит — даже если дежурный сменился пять минут назад.
:::

```svg
@service-stable-address
```

У каждого Pod — свой IP, и он **меняется** при пересоздании Pod (сессия 2.2: удалили — создался новый, с новым IP). Если другой сервис запомнит этот IP — связь оборвётся при первом же перезапуске. **Service** решает это: он не «куда-то ведёт» сам, а **постоянно следит** (через `selector`, то есть по labels, шаг 2.4), какие Pod сейчас подходят, и держит актуальный список их адресов — **endpoints**.

```bash run
cd ~/kubernetes-lab
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Service
metadata:
  name: coffeeshop-api
spec:
  selector:
    app: coffeeshop-api
  ports:
    - port: 80
      targetPort: 3000
EOF
kubectl get svc coffeeshop-api
kubectl get endpoints coffeeshop-api
```

### result
```out auto
```

Разберём поля:

- **`selector: app: coffeeshop-api`** — «найди все Pod с такой меткой» (у нашего Pod из шага 3.2 она есть).
- **`port: 80`** — порт, на котором **сам Service** доступен другим Pod в кластере.
- **`targetPort: 3000`** — порт, на котором **реально слушает** контейнер внутри Pod (наш API слушает 3000, как и в Docker-/Traefik-лабе).
- Тип Service по умолчанию — **`ClusterIP`**: у Service появляется свой стабильный виртуальный IP, **доступный только внутри кластера** (другие типы — в сессии 5).

`kubectl get endpoints coffeeshop-api` показывает **реальный** список `IP:port` Pod, которые сейчас подходят под selector — если список пуст, значит Service «не видит» ни одного живого Pod (частая причина — несовпадение labels, см. 🔨-шаг сессии 2).

### why
Service — это тот самый механизм, который заменяет DNS-имена сервисов из Docker Compose (`http://api:3000`), но надёжнее: Compose полагался на то, что имя контейнера не меняется, а Kubernetes вообще не привязывается к конкретным Pod — endpoints пересчитываются автоматически при каждом изменении набора Pod.

### deep Round robin между Pod
Когда под selector попадает несколько Pod, `kube-proxy` распределяет входящие соединения между их IP примерно равномерно (round robin, с нюансами в зависимости от режима — `iptables` или `IPVS`). Это — встроенная **базовая** балансировка нагрузки, безо всякого Ingress.

### deep Если не получилось
- **`endpoints` пуст** — сверь `selector` Service и `labels` Pod буквально (шаг 2.4); либо Pod не в фазе `Running`/`Ready` (готовность — сессия 8.2, пока проверь хотя бы `Running`).
- **Запрос к Service работает изнутри кластера, но ты пытаешься достучаться с Mac напрямую** — `ClusterIP` специально недостижим снаружи; для доступа с хоста — следующий шаг (`port-forward`).

### quiz
- Что делает Service, если IP Pod за ним меняется?
- Чем `port` отличается от `targetPort` в манифесте Service?
- Что показывает `kubectl get endpoints` и когда этот список оказывается пустым?

### links
- https://kubernetes.io/docs/concepts/services-networking/service/ | Service | Kubernetes: Service
- https://kubernetes.io/docs/concepts/services-networking/service/#virtual-ips-and-service-proxies | как работает ClusterIP | Kubernetes: Virtual IPs

## 3.5 Доступ: port-forward и DNS кластера | short: port-forward и DNS | est: ~30 мин
### intro
**Слова шага:** *`kubectl port-forward`*, *CoreDNS*, *`<service>.<namespace>.svc.cluster.local`*.

:::tip Если совсем просто
`port-forward` — это временный телефонный провод, который ты лично протягиваешь от своего ноутбука прямо к одному Pod или Service: удобно для проверки «а оно вообще отвечает», но провод исчезает, если ты закрыла терминал, и его явно не стоит использовать как постоянный способ открыть сервис наружу — для этого есть Ingress (сессия 5).
:::

```bash run
kubectl port-forward svc/coffeeshop-api 8080:80 &
sleep 2
curl -s http://localhost:8080/health
kill %1
```

### result
```out auto
```

`kubectl port-forward svc/coffeeshop-api 8080:80` открывает порт `8080` на твоём Mac и проксирует его **через API-сервер** (не напрямую по сети) в порт `80` Service — удобно для быстрой проверки без доступа снаружи кластера.

**DNS внутри кластера.** Каждый Service автоматически получает DNS-имя вида `coffeeshop-api.default.svc.cluster.local` (или просто `coffeeshop-api`, если обращаться из того же namespace) — за это отвечает `CoreDNS` (которую мы видели в `kube-system`, шаг 2.1). Проверим из Pod внутри кластера:

```bash run
kubectl run dns-test --image=busybox:1.36 --rm -it --restart=Never -- nslookup coffeeshop-api
```

### result
```out auto
```

### why
Понимание, что DNS-имя сервиса «просто работает» внутри кластера — то, что заменяет ручной IP или `/etc/hosts` из Docker-лабы. API CoffeeShop может ходить к базе данных по имени `db` (сессия 6) ровно как ходил в Compose — разница только в том, что это DNS-имя резолвится в **текущий IP Service**, а не контейнера.

### deep Полное имя DNS и зачем оно длинное
`<service>.<namespace>.svc.cluster.local` — короткого имени `coffeeshop-api` достаточно только из **того же** namespace; из другого namespace нужно хотя бы `coffeeshop-api.default` (сессия 8.1 про namespace); полное имя с `svc.cluster.local` нужно редко — только когда настраиваешь что-то, что должно явно не путать Service с внешним доменом с похожим именем.

### deep Если не получилось
- **`port-forward`: `error: unable to listen on any of the requested ports`** — порт 8080 занят на Mac; возьми другой слева в `8080:80`.
- **`nslookup` не находит имя** — сверь, что Service и тестовый Pod в одном namespace (`default` по умолчанию), и что имя Service набрано без опечаток.

### quiz
- Через что реально проходит трафик при `kubectl port-forward` — напрямую по сети или иначе?
- Как получить DNS-имя Service внутри кластера и чем короткое имя отличается от полного?
- Почему `port-forward` не подходит как постоянный способ открыть сервис для реальных пользователей?

### links
- https://kubernetes.io/docs/tasks/access-application-cluster/port-forward-access-application-cluster/ | port-forward | Kubernetes: Port Forward
- https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/ | DNS для Service и Pod | Kubernetes: DNS for Services and Pods

## 3.6 Образ в kind: kind load docker-image | short: Образ в kind | est: ~30 мин
### intro
**Слова шага:** *`kind load docker-image`*, *`imagePullPolicy`*, *локальный registry*.

:::tip Если совсем просто
Твой Mac и кластер `kind` — это как два разных дома с разными холодильниками: то, что ты купила (собрала образ) в холодильнике на кухне (локальный Docker), автоматически не появляется в холодильнике у соседей (узлы `kind`). `kind load docker-image` — это ты лично отнесла пакет продуктов туда руками.
:::

Мы уже собрали `coffeeshop-api:v1` в шаге 1.3 — но кластер `kind` **не видит** локальный Docker Desktop напрямую: его узлы — отдельные контейнеры со своим `containerd` внутри.

```bash run
kind load docker-image coffeeshop-api:v1 --name coffeeshop
docker exec coffeeshop-worker crictl images 2>&1 | grep coffeeshop
```

### result
```out auto
```

`kind load docker-image` достаёт образ из твоего локального Docker и **копирует** его прямо в containerd каждого узла кластера — после этого Pod на любом узле может запустить его без похода в интернет.

`imagePullPolicy` в манифесте Pod определяет, когда Kubernetes имеет право скачивать образ заново:

- **`IfNotPresent`** (по умолчанию для тегов, отличных от `latest`) — если образ уже есть на узле, использовать его, не качать заново. Это то, что нам нужно для `coffeeshop-api:v1`, загруженного через `kind load`.
- **`Always`** (по умолчанию для тега `latest`) — качать каждый раз перед запуском, даже если образ уже на узле.
- **`Never`** — никогда не качать, только локальный; если образа нет — ошибка `ErrImageNeverPull` (увидим в следующем шаге).

### why
Это одна из тех вещей, которая работает «сама» в облачном кластере (туда все образы попадают только через настоящий registry — Docker Hub, GHCR, ECR — куда узлы и так ходят за скачиванием) и требует лишнего шага именно в учебном `kind`. Если забыть про `kind load` — Kubernetes попытается **скачать** образ из интернета под тем же именем и не найдёт его там (`coffeeshop-api` не существует ни в одном публичном registry).

### deep Как ещё можно
Поднять **локальный registry** (контейнер `registry:2`, подключённый к сети `kind`) и `docker push`/`pull` через него — так ближе к реальному облаку, но для учебных целей `kind load` быстрее и проще; подробно — ссылка ниже, в лабе мы используем `kind load`.

### deep Если не получилось
- **После `kind load` образ всё равно не находится** — проверь, что указала правильное имя кластера (`--name coffeeshop`, как в шаге 1.5); `kind get clusters` покажет все существующие.
- **Образ загрузила, но Pod создала раньше** — `kind load` не переcоздаёт уже существующие Pod; удали и создай Pod заново или это сделает Deployment при следующем rollout (сессия 4).

### quiz
- Почему образ, собранный локально на Mac, не виден автоматически узлам `kind`?
- Чем отличаются `imagePullPolicy: IfNotPresent` и `Always`?
- Что происходит, если `imagePullPolicy: Never`, а образа на узле нет?

### links
- https://kind.sigs.k8s.io/docs/user/quick-start/#loading-an-image-into-your-cluster | загрузка образа в kind | kind: Loading an Image
- https://kubernetes.io/docs/concepts/containers/images/#image-pull-policy | imagePullPolicy | Kubernetes: Image Pull Policy

## 3.7 🔨 ImagePullBackOff и ErrImageNeverPull | short: 🔨 ImagePullBackOff | est: ~30 мин
### intro
**Слова шага:** *`ImagePullBackOff`*, *`ErrImageNeverPull`*, *`ErrImagePull`*, *экспоненциальная задержка*.

:::tip Если совсем просто
`ImagePullBackOff` — Kubernetes честно говорит: «я пыталась скачать образ, не получилось, подожду немного и попробую снова, и каждый раз жду дольше». Это не намертво зависший статус — это терпеливый повтор с нарастающей паузой, пока причина не будет исправлена.
:::

Два варианта поломки — опечатка в имени образа и `imagePullPolicy: Never` без локального образа:

```bash run
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: broken-typo
spec:
  containers:
    - name: api
      image: coffeeshop-api:v99-does-not-exist
EOF
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: broken-neverpull
spec:
  containers:
    - name: api
      image: coffeeshop-api:v1
      imagePullPolicy: Never
EOF
sleep 10
kubectl get pods broken-typo broken-neverpull
kubectl describe pod broken-typo | tail -8
```

### result
```out auto
```

- **`broken-typo`** — тега `v99-does-not-exist` не существует ни локально, ни в каком-либо registry (образ `coffeeshop-api` вообще никуда не публиковался — он существует только как результат `kind load`). Статус пройдёт через `ErrImagePull` (первая попытка, явная ошибка) к **`ImagePullBackOff`** (повторные попытки с нарастающей паузой: 10 с, 20 с, 40 с… до потолка).
- **`broken-neverpull`** (если этот Pod на узле, куда образ `coffeeshop-api:v1` не загружали `kind load`, или если он вообще не был загружен) — статус **`ErrImageNeverPull`**: `imagePullPolicy: Never` запрещает любую попытку скачивания, и раз локально образа нет — тупик, который сам себя не починит, в отличие от `ImagePullBackOff`.

**Починка:** для `broken-typo` — исправить тег на существующий (`v1`); для `broken-neverpull` — либо убрать `imagePullPolicy: Never` (тогда Kubernetes попробует скачать из registry, тоже не найдёт — здесь это не поможет, так как образ не публичный), либо убедиться, что `kind load docker-image` выполнен для **того узла**, куда Pod запланирован.

```bash run
kubectl delete pod broken-typo broken-neverpull
```

### why
Разница между `ImagePullBackOff` (повторяется, может сам исправиться, если причина временная — например, недоступность registry) и `ErrImageNeverPull` (не повторится никогда без твоего участия, потому что политика это прямо запрещает) — ключевая для того, чтобы не ждать вечно то, что само не произойдёт.

### deep Если не получилось
- **Образ приватный, и дело не в опечатке** — для приватных registry нужен `imagePullSecrets` (тип Secret `dockerconfigjson`, сессия 7.3); без него будет `ErrImagePull: unauthorized`.
- **`kind load` выполнила, а всё равно `ImagePullBackOff`** — проверь, на какой узел **реально** запланирован Pod (`kubectl get pod -o wide`); если кластер из нескольких worker-узлов, `kind load` по умолчанию грузит на все узлы кластера с этим именем — но при явном указании `--nodes` может ограничиться одним.

### quiz
- Чем `ImagePullBackOff` отличается от `ErrImageNeverPull` по тому, может ли ситуация исправиться сама?
- Что means экспоненциальная задержка в контексте повторных попыток Kubernetes?
- Какая дополнительная настройка нужна, чтобы тянуть образ из приватного registry?

### links
- https://kubernetes.io/docs/concepts/containers/images/ | образы контейнеров | Kubernetes: Images
- https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/ | образы из приватного registry | Kubernetes: Pull an Image from a Private Registry

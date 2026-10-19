# Сессия 2 · Архитектура и объекты
dur: ~4 ч

## 2.1 Компоненты кластера: путь `apply` | short: Путь apply | est: ~35 мин
### intro
**Слова шага:** *`kube-apiserver`*, *`etcd`*, *`scheduler`*, *`controller manager`*, *`kubelet`*, *`kube-proxy`*, *`containerd`*.

:::tip Если совсем просто
Представь почту. Ты приносишь письмо (манифест) **в приёмное окно** (`kube-apiserver`) — там его проверяют и регистрируют (`etcd` — архив всех писем). Диспетчер (`scheduler`) смотрит, в какое отделение (узел) письмо повезти. Там курьер (`kubelet`) его вскрывает и физически выполняет: звонит на склад (`containerd`), чтобы собрать посылку (контейнер).
:::

```svg
@apply-path
```

Шесть компонентов, которые должны сработать, чтобы `kubectl apply -f pod.yaml` закончился работающим контейнером:

1. **`kube-apiserver`** (на control-plane) — единственная дверь в кластер. Всё (и `kubectl`, и любой другой компонент) общается только с ним, через REST API. Проверяет манифест (валидный YAML? известный `kind`? прав у тебя достаточно?) и сохраняет его.
2. **`etcd`** (на control-plane) — база данных «ключ-значение», единственное место, где кластер **хранит** всё своё состояние. Если `etcd` потерян без резервной копии — потерян весь кластер.
3. **`scheduler`** (на control-plane) — следит за новыми Pod без узла и решает, **на каком** узле его запустить (по ресурсам, ограничениям, affinity — сессия 8 и далее).
4. **`controller manager`** (на control-plane) — набор циклов «сверить желаемое с текущим»: это он следит, что у Deployment нужное число Pod (сессия 4), что PVC привязан к PV (сессия 6) и так далее.
5. **`kubelet`** (на **каждом** узле, и control-plane, и worker) — агент, который получает от API-сервера список Pod, назначенных **этому** узлу, и следит, что они реально работают.
6. **`kube-proxy`** и **`containerd`** (на каждом узле) — `containerd` реально запускает контейнеры (аналог Docker-демона, Kubernetes сам контейнеры не запускает), `kube-proxy` настраивает сеть для Service (сессия 3 и 5).

Посмотрим на всё это внутри нашего `kind`-кластера:

```bash run
kubectl get pods -n kube-system -o wide
kubectl get componentstatuses 2>&1 | head -5
```

### result
```out auto
```

В namespace `kube-system` видны Pod `etcd-coffeeshop-control-plane`, `kube-apiserver-coffeeshop-control-plane`, `kube-scheduler-...`, `kube-controller-manager-...` (все четыре — только на control-plane) и по экземпляру `kube-proxy` и `coredns` на каждом узле (`kindnet` — сетевой плагин `kind`). `kubelet` и `containerd` Pod'ами не являются: это процессы прямо на узле (не в кластере), поэтому их здесь не видно — проверить их можно только зайдя в сам узел-контейнер (`docker exec`).

### why
Когда что-то не создаётся или не планируется, вопрос «на каком из шести шагов это застряло» сразу сокращает круг поиска: не создаётся вообще — проблема до API-сервера (синтаксис, права); создан, но без узла — `scheduler`; есть на узле, но не запускается — `kubelet`/`containerd`; есть, но нет сети — `kube-proxy`/CNI.

### deep Почему control-plane компоненты сами — Pod
Да, `etcd`, `kube-apiserver` и другие компоненты control plane в современных кластерах (и в `kind`) сами запущены как **статические Pod** — манифесты для них лежат прямо в файловой системе узла, и `kubelet` поднимает их при старте, даже до того, как API-сервер вообще появился (курица и яйцо решается тем, что `kubelet` может работать и без API-сервера, читая файлы локально).

### deep Если не получилось
- **`kubectl get componentstatuses` ругается предупреждением об устаревании** — это ожидаемо, API помечен deprecated с версии 1.19; для реальной диагностики компонентов используй `kubectl get pods -n kube-system`.
- **Каких-то Pod в `kube-system` нет** — кластер мог не успеть полностью подняться после шага 1.5; подожди и повтори.

### quiz
- Через какой единственный компонент проходит абсолютно любое обращение к кластеру?
- Чем отличаются роли `scheduler` и `kubelet`?
- Почему потеря `etcd` без резервной копии — это потеря всего кластера?

### links
- https://kubernetes.io/docs/concepts/overview/components/ | компоненты кластера | Kubernetes: Components
- https://kubernetes.io/docs/concepts/architecture/control-plane-node-communication/ | связь control plane и узлов | Kubernetes: Control Plane-Node Communication

## 2.2 Желаемое и текущее: reconcile | short: Reconcile-цикл | est: ~30 мин
### intro
**Слова шага:** *желаемое состояние*, *текущее состояние*, *reconcile (сверка)*, *контроллер*.

:::tip Если совсем просто
Термостат не «выключает» отопление один раз — он **постоянно** сверяет температуру в комнате с той, что ты задала, и включает/выключает батарею заново и заново. Контроллеры Kubernetes работают так же: не «выполнили команду один раз», а бесконечно сверяют «что хочу» с «что есть» и подправляют реальность, если она отклонилась — даже если отклонение вызвала не ты (кто-то вручную удалил Pod).
:::

Проверим это не описанием, а экспериментом в следующем шаге (2.6) — а сейчас зафиксируем идею словами, без которых дальше ничего не объяснить:

- **Желаемое состояние** — то, что лежит в `etcd` после твоего `kubectl apply` (манифест).
- **Текущее состояние** — то, что реально работает на узлах прямо сейчас.
- **Reconcile** («сверка», «примирение») — бесконечный цикл: контроллер читает желаемое, читает текущее, и если они расходятся — делает шаг к тому, чтобы текущее стало похоже на желаемое. Не «мгновенно телепортирует», а именно **шаг**: удалить Pod → создать новый Pod того же типа → ждать, пока он станет `Ready`.

### result
Запускать здесь ничего не будем — эксперимент («удалить Pod руками и посмотреть, что будет») сделаем в шаге 2.6, когда у нас уже будут команды `get`/`delete`. Держи в голове одно: **Kubernetes никогда не говорит «готово» в смысле «один раз выполнено и забыто»** — он непрерывно пытается удержать состояние.

### why
Это объясняет, почему, например, удаление Pod, управляемого Deployment, не «освобождает ресурсы навсегда», а вызывает создание нового Pod — реконсиляция увидела расхождение (было 3 реплики, стало 2) и исправила его. Без этой идеи поведение Kubernetes кажется непредсказуемым; с ней — наоборот, предсказуемым до буквальности.

### deep Что если желаемое состояние противоречиво
Контроллер делает, что может, и **сообщает об ошибке через статус объекта и события** (сессия 8.6), а не отказывается молча. Пример: просишь PVC с `StorageClass`, которого не существует — PVC останется в `Pending` вечно, с понятной причиной в `describe`.

### deep Reconcile — не только у Kubernetes
Та же идея — в Terraform (`plan`/`apply` сравнивают желаемое с реальной инфраструктурой), в React (виртуальный DOM сверяется с реальным). Если ты видела `diff` в Terraform — это тот же принцип другими словами.

### quiz
- Чем «желаемое состояние» отличается от «текущего» и где желаемое хранится?
- Почему reconcile — это бесконечный цикл, а не одноразовое действие?
- Что произойдёт, если желаемое состояние в принципе невыполнимо?

### links
- https://kubernetes.io/docs/concepts/architecture/controller/ | контроллеры | Kubernetes: Controllers
- https://kubernetes.io/docs/concepts/overview/components/#kube-controller-manager | kube-controller-manager | Kubernetes: kube-controller-manager

## 2.3 Императивно и декларативно | short: `run`/`create` vs `apply` | est: ~30 мин
### intro
**Слова шага:** *императивная команда*, *декларативный манифест*, *`kubectl run`*, *`kubectl create`*, *`kubectl apply`*.

:::tip Если совсем просто
«Поставь чайник» (императив: ты говоришь, какое действие совершить прямо сейчас) и «на кухне должен всегда стоять горячий чайник» (декларатив: правило, которое кто-то поддерживает сам, пока ты не отменишь). `kubectl run` — первое, `apply -f файл.yaml` — второе.
:::

Три команды, которые выглядят похоже, но делают разное:

```bash run
kubectl run demo --image=nginx:alpine --dry-run=client -o yaml | head -15
echo "---"
kubectl create deployment demo2 --image=nginx:alpine --dry-run=client -o yaml | head -15
```

### result
```out auto
```

- **`kubectl run`** — создаёт **один Pod** императивно: быстро для «попробовать образ», но без Deployment вокруг (значит, без самолечения и масштабирования, сессия 4).
- **`kubectl create`** — создаёт объект из флагов (здесь — Deployment), тоже императивно, но хотя бы с нужным типом объекта.
- **`kubectl apply -f файл.yaml`** — декларативно: ты описываешь желаемое в файле, `apply` **сравнивает** его с тем, что уже есть в кластере, и применяет только разницу; повторный `apply` того же файла **ничего не ломает** (идемпотентность) — а повторный `kubectl create` на существующее имя выдаст ошибку «уже существует».

Флаг `--dry-run=client -o yaml`, который мы использовали выше, — отличный приём: **показывает**, какой YAML команда бы создала, **без** реального создания объекта. Удобно, чтобы быстро получить шаблон манифеста и доработать его руками, вместо того чтобы писать с нуля.

### why
В лабе и в проде мы будем пользоваться почти исключительно `apply -f`: манифесты лежат в git, история правок видна в `diff`, повторное применение безопасно. Императивные команды хороши для быстрых опытов («проверить, что образ вообще стартует») — но результат такого опыта не воспроизводим и не лежит в git.

### deep Что делает `apply` под капотом
`apply` хранит в аннотации объекта (`kubectl.kubernetes.io/last-applied-configuration`) последнюю применённую версию манифеста — именно её он сравнивает со **следующим** `apply`, чтобы понять, какие поля убрать, если ты их удалила из файла. Отсюда правило: не смешивай `apply` и ручные правки через `kubectl edit` на одном объекте — `apply` может не узнать о ручной правке и откатить её при следующем запуске.

### deep Как ещё можно
`kubectl diff -f файл.yaml` — показывает, что изменится при `apply`, **без** применения; полезно перед правкой важного объекта в реальном кластере.

### quiz
- Чем `kubectl apply -f` принципиально отличается от `kubectl create` на уже существующий объект?
- Для чего удобен `--dry-run=client -o yaml`?
- Что хранится в аннотации `last-applied-configuration` и зачем она `apply`?

### links
- https://kubernetes.io/docs/tasks/manage-kubernetes-objects/declarative-config/ | декларативное управление | Kubernetes: Declarative Management
- https://kubernetes.io/docs/reference/kubectl/generated/kubectl_apply/ | справочник kubectl apply | Kubernetes: kubectl apply

## 2.4 Объект: metadata, labels, selectors | short: Объект и метки | est: ~35 мин
### intro
**Слова шага:** *`metadata`*, *`labels`*, *`selector`*, *`annotations`*, *`ownerReferences`*.

:::tip Если совсем просто
Представь склад без адресов полок, только с бирками на коробках: «кухня», «хрупкое», «срочно». Чтобы найти все хрупкие коробки, не нужен точный адрес каждой — достаточно спросить «все, у кого бирка `хрупкое`». Labels в Kubernetes — ровно такие бирки, а selector — вопрос «дай мне все с такой биркой».
:::

```bash run
kubectl run demo --image=nginx:alpine --labels=app=demo,tier=web --dry-run=client -o yaml
```

### result
```out auto
```

Разберём `metadata` по полям:

- **`name`** — уникальное имя объекта **внутри своего типа и namespace** (два Pod с одинаковым именем в одном namespace — ошибка, в разных namespace — нормально).
- **`labels`** — произвольные пары `ключ: значение` для **группировки и выбора** объектов (`app=demo`, `tier=web`). В отличие от имени, labels не обязаны быть уникальными — наоборот, их смысл в том, что у многих объектов одна и та же метка.
- **`annotations`** — тоже пары `ключ: значение`, но **не для выбора**, а для хранения произвольной информации (описание, ссылка на коммит, настройки сторонних инструментов). `kubectl get` не может искать по аннотациям так же эффективно, как по labels.
- **`ownerReferences`** — ссылка «кто меня создал» (например, у Pod, созданного Deployment через ReplicaSet, здесь будет ссылка на ReplicaSet) — по ней работает каскадное удаление и `kubectl get pods --show-labels`/`kubectl describe` показывают родителя.

**Selector** — это как раз запрос по labels: `kubectl get pods -l app=demo` вернёт все Pod с такой меткой, независимо от имени. Service использует selector, чтобы найти, какие Pod обслуживать (сессия 3) — это одна из самых важных связей во всём Kubernetes.

### why
Почти все связи между объектами в Kubernetes (Service → Pod, Deployment → Pod через ReplicaSet, NetworkPolicy → Pod) работают **не по имени**, а по **labels + selector**. Когда связь «не работает», в 9 случаях из 10 причина — несовпадение меток (опечатка, разный регистр, забытая метка на новом Pod).

### deep Как ещё можно
`kubectl label pod demo env=staging` — добавить метку существующему объекту без правки файла (но помни про риск разойтись с `apply`, шаг 2.3). `kubectl get pods --show-labels` — увидеть все метки сразу.

### deep Если не получилось
- **Selector Service не находит Pod** — сравни `kubectl get pod demo --show-labels` и `kubectl get svc demo -o yaml | grep -A3 selector` буквально символ в символ: `app: demo` и `app: Demo` — разные метки.

### quiz
- Чем labels отличаются от annotations по назначению?
- Как Service находит, какие Pod ему обслуживать?
- Что хранится в `ownerReferences` и для чего это используется?

### links
- https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/ | labels и selectors | Kubernetes: Labels and Selectors
- https://kubernetes.io/docs/concepts/overview/working-with-objects/annotations/ | annotations | Kubernetes: Annotations

## 2.5 API: группы, версии, api-resources | short: API-группы | est: ~30 мин
### intro
**Слова шага:** *API-группа*, *версия API (`v1`, `apps/v1`, …)*, *`kubectl api-resources`*, *`kubectl api-versions`*.

:::tip Если совсем просто
Представь большую библиотеку с разными отделами: «Художественная литература» (`apps`), «Справочники» (`core`, пишется просто как `v1` без имени группы) — у каждого отдела свой каталог и своя нумерация полок (версия API). Зная отдел и номер полки, ты точно найдёшь нужную книгу (тип объекта), даже если в двух отделах есть книги с похожим названием.
:::

```bash run
kubectl api-resources | grep -E 'NAME|^pods |^deployments |^services |^ingresses '
kubectl api-versions | sort | head -10
```

### result
```out auto
```

Увидим, например: `pods` — API-группа **пустая** (обозначается просто `v1`, это «ядро», core API — самые старые и базовые типы), `deployments` — группа `apps`, версия `v1` (значит, полное имя API — `apps/v1`), `ingresses` — группа `networking.k8s.io`.

Зачем это важно практически: в `apiVersion` манифеста нужно указать **именно ту** группу и версию, которую понимает твой кластер — опечатка или использование версии из другого релиза Kubernetes (документация в интернете может описывать более новую или более старую версию) даёт ошибку `no matches for kind "X" in version "Y"`.

### result
```out auto
```

### why
API Kubernetes **растёт** со временем: новые возможности сначала появляются в `v1alpha1`/`v1beta1` (экспериментальные, могут измениться без предупреждения) и только потом стабилизируются до `v1`. `kubectl api-resources`/`api-versions`, выполненные **на твоём** кластере, — единственный надёжный источник, что здесь и сейчас доступно, точнее любой статьи в интернете.

### deep Почему `Pod`/`Service` в «пустой» группе, а `Deployment` — в `apps`
Историческая причина: `Pod`, `Service`, `ConfigMap`, `Secret` и другие — самые первые типы Kubernetes, были добавлены ещё до того, как придумали разбивать API на группы; их оставили в «core»-группе для обратной совместимости. Все новые типы (включая `Deployment`, появившийся позже) получают именованную группу с первого дня.

### deep Если не получилось
- **`no matches for kind "Ingress" in version "extensions/v1beta1"`** — используешь старый пример из интернета; актуальная версия — `networking.k8s.io/v1` (сессия 5).

### quiz
- Почему `Pod` и `Service` используют просто `v1`, без имени группы?
- Что отличает `v1alpha1`/`v1beta1` от `v1` по надёжности?
- Как узнать, какие версии API понимает именно твой кластер прямо сейчас?

### links
- https://kubernetes.io/docs/reference/using-api/#api-groups | группы API | Kubernetes: API Groups
- https://kubernetes.io/docs/reference/using-api/deprecation-policy/ | политика устаревания API | Kubernetes: Deprecation Policy

## 2.6 Первые команды: get, describe, delete, diff | short: Первые команды | est: ~35 мин
### intro
**Слова шага:** *`get`*, *`describe`*, *`delete`*, *`diff`*, *`-o yaml/wide/json`*, *`jsonpath`*.

:::tip Если совсем просто
`get` — короткий список («что есть»), `describe` — подробная карточка одного объекта с историей событий («что с ним происходило»), `delete` — убрать. Если `get` — это заголовок новости, `describe` — вся статья.
:::

Создадим Pod декларативно и понаблюдаем за reconcile-циклом из шага 2.2 в действии:

```bash run
cd ~/kubernetes-lab
mkdir -p manifests
cat > manifests/00-demo-pod.yaml <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: demo
  labels:
    app: demo
spec:
  containers:
    - name: nginx
      image: nginx:alpine
EOF
kubectl apply -f manifests/00-demo-pod.yaml
kubectl get pods -o wide
kubectl get pod demo -o jsonpath='{.status.podIP}{"\n"}'
```

### result
```out auto
```

Теперь удалим Pod **руками**, минуя файл, и посмотрим, что сделает Kubernetes:

```bash run
kubectl delete pod demo
sleep 2
kubectl get pods
```

### result
```out auto
```

Pod пропал и **не вернулся сам** — и это ожидаемо: голый `Pod` (без Deployment) не имеет контроллера, который следил бы за «должно быть 1 реплика». Самолечение появится только с Deployment (сессия 4) — здесь важно увидеть разницу самому, а не поверить на слово.

Вернём Pod и попробуем `describe` и `diff`:

```bash run
kubectl apply -f manifests/00-demo-pod.yaml
sleep 2
kubectl describe pod demo | tail -15
echo "--- что изменится при правке образа ---"
sed -i '' 's/nginx:alpine/nginx:1.27-alpine/' manifests/00-demo-pod.yaml 2>/dev/null || sed -i 's/nginx:alpine/nginx:1.27-alpine/' manifests/00-demo-pod.yaml
kubectl diff -f manifests/00-demo-pod.yaml
```

### result
```out auto
```

`kubectl describe pod demo` заканчивается блоком **Events** — хронологией того, что произошло с объектом (`Scheduled`, `Pulled`, `Created`, `Started`); это первое место, куда смотреть при любой проблеме (сессия 8.6 — целая таблица типичных событий). `kubectl diff` показал бы разницу между тем, что в кластере, и тем, что в файле (здесь — смену тега образа) **без** применения.

### why
`describe` — не просто «подробный `get`»: блок Events — единственное место, где видна **история**, а не только текущее состояние. Когда Pod не поднимается, 90% причины находится там за десять секунд, а не за десять минут гадания.

### deep Команды по частям
`-o jsonpath='{.status.podIP}{"\n"}'` — вытащить одно конкретное поле из JSON-представления объекта без `jq`, встроенными средствами `kubectl`; `{"\n"}` добавляет перевод строки, которого `jsonpath` сам не ставит. `sed -i ''` (с пустой строкой после `-i`) — версия для BSD/macOS `sed`; на Linux `-i` без аргумента.

### deep Если не получилось
- **`kubectl diff` требует `KUBE_EDITOR` или падает на правах** — на части систем `diff` использует внешний `diff`-бинарник; если ошибка про него — `brew install diffutils` или просто читай результат `kubectl get -o yaml` до и после.
- **Pod всё-таки «вернулся» после `delete` без твоего participation** — проверь, не создала ли ты его через `kubectl run` ранее под тем же именем с Deployment — тогда это не тот голый Pod, а управляемый.

### quiz
- Почему голый `Pod` не восстанавливается сам после `kubectl delete`, а управляемый Deployment — восстанавливается?
- Где смотреть историю происходящего с объектом, а не только текущий статус?
- Что показывает `kubectl diff -f файл.yaml` и чем это отличается от `kubectl apply`?

### links
- https://kubernetes.io/docs/reference/kubectl/cheatsheet/ | шпаргалка kubectl | Kubernetes: kubectl Cheat Sheet
- https://kubernetes.io/docs/reference/kubectl/jsonpath/ | синтаксис jsonpath | Kubernetes: JSONPath Support

## 2.7 🔨 «apply ничего не делает»: опечатка в kind | short: 🔨 Опечатка в kind | est: ~25 мин
### intro
**Слова шага:** *валидация манифеста*, *опечатка в `kind`*, *«тихий» отказ*.

:::tip Если совсем просто
Напиши на конверте не «Письмо», а «Пизьмо» — почта всё равно разберётся и чаще всего вернёт его тебе с пометкой «не понимаю, что это». Так и `kubectl apply`: при опечатке в `kind` или `apiVersion` он не создаёт «что-то странное» — он отказывает прямо в терминале, явно. Пугает другое: когда отказа не видно, потому что команда была в скрипте, а вывод никто не читал.
:::

```bash run
cd ~/kubernetes-lab
cat > manifests/broken-pod.yaml <<'EOF'
apiVersion: v1
kind: Podd
metadata:
  name: broken
spec:
  containers:
    - name: nginx
      image: nginx:alpine
EOF
kubectl apply -f manifests/broken-pod.yaml
echo "код выхода: $?"
```

### result
```out auto
```

`kubectl apply` ответил ошибкой `no matches for kind "Podd" in version "v1"` и завершился **ненулевым кодом выхода** (проверь строкой `echo "код выхода: $?"` — это важно: в скриптах и CI именно код выхода решает, продолжать дальше или остановиться). Объект **не создан** — поищи его в `kubectl get pods`, его там нет.

Опаснее другой случай — опечатка не в `kind`, а внутри `spec`, в поле, которого тип объекта не ожидает: такие поля Kubernetes по правилам валидации (`strict`, по умолчанию с версии 1.25+) тоже отклоняет с ошибкой, но раньше (и в некоторых инструментах до сих пор) они могли тихо проигнорироваться.

```bash run
cat > manifests/broken-field.yaml <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: broken2
spec:
  continers:
    - name: nginx
      image: nginx:alpine
EOF
kubectl apply -f manifests/broken-field.yaml
```

### result
```out auto
```

Современный `kubectl` ловит и это: `error: unknown field "spec.continers"`.

### why
Привычка проверять **код выхода** команды (`$?` или просто не игнорировать вывод в скриптах/CI) — то, что отличает «автоматизацию, которой доверяют» от «автоматизации, которая однажды тихо ничего не сделала и никто не заметил». В CI-пайплайне (сессия 14, Helm) это ровно тот механизм, который должен остановить деплой, если `apply`/`helm upgrade` провалился.

### deep Если не получилось
- **Ошибки не видно, команда «прошла»** — проверь, не используешь ли флаг `--validate=false` где-то в своей истории команд: он отключает именно эту проверку (и делать это специально — почти всегда плохая идея).

### quiz
- Что произойдёт с кодом выхода `kubectl apply`, если манифест содержит опечатку в `kind`?
- Почему важно проверять код выхода команд в скриптах, а не только текст вывода?
- Какая разница между «тихим» игнорированием неизвестного поля и явной ошибкой валидации?

### links
- https://kubernetes.io/docs/reference/using-api/server-side-apply/ | server-side apply и валидация | Kubernetes: Server-Side Apply
- https://kubernetes.io/docs/concepts/overview/working-with-objects/kubernetes-objects/ | понятие объекта Kubernetes | Kubernetes: Kubernetes Objects

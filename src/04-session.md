# Сессия 4 · Deployment и обновления
dur: ~4 ч

## 4.1 Deployment → ReplicaSet → Pod | short: Зачем Deployment | est: ~35 мин
### intro
**Слова шага:** *Deployment*, *ReplicaSet*, *реплика*, *самолечение*.

:::tip Если совсем просто
Голый Pod из сессии 3 — это сотрудник без начальника: уволился (упал) — никто не нанял замену. Deployment — начальник отдела, у которого в штатном расписании написано «в отделе должно быть 3 человека»: если кто-то уходит, начальник **сразу** нанимает замену, и тебе не нужно самой следить за вакансиями.
:::

Deployment не управляет Pod напрямую — между ними есть посредник, **ReplicaSet**:

```text
Deployment  (стратегия обновления, история версий)
    └── ReplicaSet  (просто: "должно быть N штук вот таких Pod")
            └── Pod × N
```

Удалишь Pod — ReplicaSet замечает «было 3, стало 2» и создаёт новый (reconcile из сессии 2.2). Поправишь образ в Deployment — создастся **новый** ReplicaSet (с новой версией Pod), а старый постепенно «сдуется» до нуля (это и есть rolling update, шаг 4.3). Старые ReplicaSet не удаляются совсем — несколько последних хранятся для истории и быстрого отката (шаг 4.4).

```bash run
cd ~/kubernetes-lab
kubectl delete pod coffeeshop-api --ignore-not-found
cat > manifests/02-deployment-api.yaml <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: coffeeshop-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: coffeeshop-api
  template:
    metadata:
      labels:
        app: coffeeshop-api
    spec:
      containers:
        - name: api
          image: coffeeshop-api:v1
          ports:
            - containerPort: 3000
EOF
kubectl apply -f manifests/02-deployment-api.yaml
kubectl get deployment,replicaset,pod -l app=coffeeshop-api
```

### result
```out auto
```

Три уровня объектов видны разом: Deployment `coffeeshop-api` (желаемое: 2 реплики), один ReplicaSet (имя с суффиксом-хэшем, например `coffeeshop-api-7d9f8c6b5`), и два Pod с тем же хэшем в имени — это **не случайность**: хэш считается от содержимого `template` (шаблона Pod), поэтому у нового ReplicaSet при изменении образа будет **другой** хэш.

Проверим самолечение так же, как проверяли в сессии 2.2, но теперь с Deployment:

```bash run
pod1=$(kubectl get pods -l app=coffeeshop-api -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod "$pod1"
sleep 3
kubectl get pods -l app=coffeeshop-api
```

### result
```out auto
```

На этот раз удалённый Pod **заменился новым** за секунды — reconcile ReplicaSet увидел «было 2, стало 1» и создал недостающий.

### why
Это объясняет, почему в проде почти никогда не создают голые Pod напрямую: Deployment (а позже — StatefulSet, Job, CronJob для специальных случаев) даёт самолечение и управляемые обновления практически бесплатно, одним дополнительным слоем объектов.

### deep Структура `template`
Поле `spec.template` внутри Deployment — это **целое описание Pod** (своя `metadata` с labels, свой `spec` с контейнерами) — именно его копирует ReplicaSet при создании каждой реплики. `spec.selector.matchLabels` должен совпадать с `spec.template.metadata.labels` — иначе Kubernetes откажет в создании Deployment (`selector does not match template labels`).

### deep Если не получилось
- **ReplicaSet создался, но 0 Pod** — проверь `kubectl describe replicaset <имя>`, события там те же, что у Pod (ресурсы, образ).
- **`selector does not match template labels`** — поправь `matchLabels` или `template.metadata.labels` так, чтобы совпадали буквально.

### quiz
- Какую роль играет ReplicaSet между Deployment и Pod?
- Что происходит со старым ReplicaSet при обновлении образа в Deployment?
- Почему голые Pod на практике используют редко?

### links
- https://kubernetes.io/docs/concepts/workloads/controllers/deployment/ | Deployment | Kubernetes: Deployment
- https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/ | ReplicaSet | Kubernetes: ReplicaSet

## 4.2 Реплики и масштабирование | short: scale | est: ~25 мин
### intro
**Слова шага:** *`kubectl scale`*, *`replicas`*, *декларативное масштабирование*.

:::tip Если совсем просто
Хочешь больше касс в кофейне в выходные — меняешь цифру в штатном расписании (`replicas` в манифесте), а не нанимаешь людей лично по одному. `kubectl scale` — это быстрый способ поменять именно эту цифру без похода в файл, но с тем же результатом.
:::

```bash run
kubectl scale deployment coffeeshop-api --replicas=4
kubectl get pods -l app=coffeeshop-api
```

### result
```out auto
```

Четыре Pod вместо двух, появились за несколько секунд. Это **императивная** команда (сессия 2.3) — она меняет число в реальном объекте, но **не** в твоём файле `manifests/02-deployment-api.yaml`. Если ты потом применишь файл заново без правки, `replicas` вернётся к 2 — это та самая ловушка «разошлось с источником правды», о которой говорили в сессии 2.3.

Правильный декларативный путь — поправить файл:

```bash run
sed -i '' 's/replicas: 2/replicas: 3/' manifests/02-deployment-api.yaml 2>/dev/null || sed -i 's/replicas: 2/replicas: 3/' manifests/02-deployment-api.yaml
kubectl apply -f manifests/02-deployment-api.yaml
kubectl get pods -l app=coffeeshop-api
```

### result
```out auto
```

### why
`kubectl scale` отлично подходит для разового «прямо сейчас нужно больше» или для скриптов автоматизации (а в сессии 10 число реплик вообще будет менять HPA — автоматический контроллер, тоже без правки файла). Но если ты держишь манифесты в git как источник правды — конечное число должно оказаться и там, иначе следующий `apply` всех удивит, откатив изменение.

### deep Если не получилось
- **После `apply` число реплик «прыгнуло» неожиданно** — почти всегда это и есть ситуация выше: кто-то (ты сама, HPA, CI) поменял `replicas` напрямую, а файл не обновили.

### quiz
- Чем `kubectl scale` отличается от правки `replicas` в файле по итоговому эффекту на git?
- Что произойдёт при следующем `apply` файла, если `replicas` в кластере и в файле разошлись?

### links
- https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#scaling-a-deployment | масштабирование Deployment | Kubernetes: Scale a Deployment

## 4.3 Rolling update: maxSurge и maxUnavailable | short: Rolling update | est: ~40 мин
### intro
**Слова шага:** *rolling update*, *`maxSurge`*, *`maxUnavailable`*, *`minReadySeconds`*.

:::tip Если совсем просто
Конвейер на заводе не останавливают целиком, чтобы заменить деталь: старую деталь снимают, новую ставят, лента едет дальше, и в любой момент почти все места на ленте заняты. Rolling update — то же самое с Pod: по одной (или несколько) старые версии заменяются новыми, а сервис всё это время продолжает отвечать.
:::

```svg
@rolling-update-wave
```

```bash run
cat >> manifests/02-deployment-api.yaml <<'EOF'
EOF
kubectl patch deployment coffeeshop-api --type=strategic -p '
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  minReadySeconds: 5
'
kubectl set image deployment/coffeeshop-api api=coffeeshop-api:v1 --record=false
kubectl rollout status deployment/coffeeshop-api
```

### result
```out auto
```

Разберём параметры стратегии `RollingUpdate` (это стратегия по умолчанию, в отличие от `Recreate`, шаг 4.6):

- **`maxSurge: 1`** — на время обновления разрешено **превысить** желаемое число реплик максимум на 1 (новый Pod поднимается, пока старый ещё жив — значит, пропускной способности становится **больше**, а не меньше).
- **`maxUnavailable: 0`** — в любой момент недоступно **ноль** реплик (новый Pod должен стать готовым, прежде чем старый начнут гасить) — это то, что даёт **обновление без простоя**.
- **`minReadySeconds: 5`** — новый Pod должен провести в статусе «готов» хотя бы 5 секунд, прежде чем считаться по-настоящему готовым (защита от «готов, но тут же упал»).

И `maxSurge`, и `maxUnavailable` можно задавать как число или как процент (`25%`) от желаемого числа реплик — при больших Deployment процент удобнее.

### why
Комбинация `maxSurge: 1, maxUnavailable: 0` — классическая настройка для **production без простоя**: пользователь в любой момент обслуживания видит рабочую версию (старую или новую), просто за счёт временного превышения числа Pod на единицу. Это ровно то, что мы делали вручную в Docker-лабе через canary/blue-green у Traefik (сессия 6 Traefik-лабы) — Deployment делает это сам, без дополнительного прокси-трюка.

### deep Если не получилось
- **Rollout «висит», не заканчивается** — почти всегда новый Pod не становится `Ready` (нет проб готовности — сессия 8.2 — или приложение реально не стартует); `kubectl rollout status` зависает именно по этой причине, и `Ctrl+C` его не чинит, чинит только Pod.
- **`maxUnavailable: 0` и `maxSurge: 0` одновременно** — тупиковая конфигурация: обновление не может сдвинуться ни в одну сторону; Kubernetes такое отклонит.

### quiz
- Что означают `maxSurge` и `maxUnavailable` и как их сочетание даёт обновление без простоя?
- Зачем нужен `minReadySeconds`, если проба готовности уже прошла?
- Чем rolling update отличается от ручного canary через веса в Traefik?

### links
- https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#rolling-update-deployment | rolling update | Kubernetes: Rolling Update Deployment
- https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#max-unavailable | maxUnavailable и maxSurge | Kubernetes: Max Unavailable

## 4.4 rollout status, history, undo | short: rollout и откат | est: ~35 мин
### intro
**Слова шага:** *`kubectl rollout status/history/undo/pause/resume`*, *ревизия*.

:::tip Если совсем просто
`rollout history` — это дневник всех версий, которые когда-либо выкатывались («версия 1: добрый образ», «версия 2: сломанный образ»). `rollout undo` — страница «вернуть, как было на прошлой записи» без необходимости помнить, что именно там было написано.
:::

```bash run
kubectl rollout history deployment/coffeeshop-api
kubectl set image deployment/coffeeshop-api api=coffeeshop-api:v2-broken
kubectl rollout status deployment/coffeeshop-api --timeout=20s 2>&1 | tail -5
```

### result
```out auto
```

Образ `coffeeshop-api:v2-broken` не существует — обновление «застревает»: старые Pod продолжают работать (это и была цель `maxUnavailable: 0` — плохая новая версия **не обрушивает** сервис), а новый висит в `ImagePullBackOff` (сессия 3.7). Самое время откатиться:

```bash run
kubectl rollout undo deployment/coffeeshop-api
kubectl rollout status deployment/coffeeshop-api
kubectl rollout history deployment/coffeeshop-api
```

### result
```out auto
```

`rollout undo` без аргументов возвращает к **предыдущей** ревизии; `kubectl rollout undo deployment/coffeeshop-api --to-revision=1` — к конкретному номеру из `rollout history`. `rollout pause`/`resume` — поставить выкатку на пауза посреди процесса (например, чтобы вручную проверить первую новую реплику, прежде чем катить остальные) и продолжить.

### why
Откат одной командой — это тот результат, ради которого стоило разбираться с ReplicaSet (шаг 4.1): старый ReplicaSet никуда не удалился, у него просто `replicas: 0` — `undo` возвращает его к нужному числу, а новый (сломанный) сводит к нулю. Никакого повторного копирования образов или пересборки — это секунды, а не минуты.

### deep Сколько ревизий хранится
По умолчанию — 10 (`spec.revisionHistoryLimit`); для ревизий, сохранённых дольше, Kubernetes хранит соответствующие старые ReplicaSet (с `replicas: 0`) — `kubectl get replicaset -l app=coffeeshop-api` покажет их все.

### deep Если не получилось
- **`rollout history` показывает «change-cause: <none>»** — без аннотации `kubernetes.io/change-cause` (ставится флагом `--record`, устаревшим, или вручную `kubectl annotate`) история не содержит текста о том, что изменилось — только номер ревизии; для реального проекта полезно подписывать причину явно.

### quiz
- Что происходит со старыми Pod во время неудачного rollout с `maxUnavailable: 0`?
- Чем `rollout undo` отличается от повторного `kubectl apply` старого файла?
- Для чего нужны `rollout pause`/`resume`?

### links
- https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#rolling-back-a-deployment | откат Deployment | Kubernetes: Rolling Back a Deployment
- https://kubernetes.io/docs/reference/kubectl/generated/kubectl_rollout/ | справочник kubectl rollout | Kubernetes: kubectl rollout

## 4.5 Проверка состояния: kubectl wait | short: kubectl wait | est: ~25 мин
### intro
**Слова шага:** *`kubectl wait`*, *условие (`--for=condition=...`)*, *скрипты и CI*.

:::tip Если совсем просто
Вместо того чтобы раз в секунду спрашивать «ну что, готово?» (как нетерпеливый пассажир), `kubectl wait` сама тихо ждёт, пока условие не станет верным (или не истечёт таймаут), и возвращает управление только тогда. Это то, что должен делать скрипт, а не человек в цикле.
:::

```bash run
kubectl wait --for=condition=Available deployment/coffeeshop-api --timeout=60s
echo "код выхода: $?"
```

### result
```out auto
```

`kubectl wait` возвращает управление **сразу**, как только условие выполнено (не ждёт полный таймаут), и завершается ненулевым кодом, если условие не выполнилось за отведённое время — это именно то, что нужно для скрипта `up.sh`/CI-пайплайна (сессия 14): «подожди, пока Deployment не станет Available, и если не дождалась за минуту — останови выкатку и сообщи об ошибке», вместо `sleep 30` наугад.

### why
`sleep N` в скриптах — постоянный источник то «слишком рано» (сервис ещё не готов), то «слишком долго» (минута впустую, когда готово было за три секунды). `kubectl wait` решает это один раз и правильно.

### deep Другие условия
`--for=condition=Ready` — для конкретного Pod; `--for=delete` — ждать, пока объект **исчезнет** (полезно после `kubectl delete`, когда нужно убедиться, что ресурс реально освободился перед следующим шагом); `--for=jsonpath='{.status.phase}'=Running` — произвольное условие по полю.

### quiz
- Чем `kubectl wait` лучше, чем `sleep 30` в скрипте запуска?
- Что возвращает `kubectl wait`, если условие не выполнилось за таймаут?

### links
- https://kubernetes.io/docs/reference/kubectl/generated/kubectl_wait/ | справочник kubectl wait | Kubernetes: kubectl wait

## 4.6 Стратегия Recreate | short: Recreate | est: ~20 мин
### intro
**Слова шага:** *стратегия `Recreate`*, *когда простой неизбежен*.

:::tip Если совсем просто
Иногда два поколения не могут жить вместе: если новая и старая версия одновременно пишут в один файл несовместимым форматом, безопаснее сначала всех выгнать (погасить старое), а потом заселить новых (поднять новое) — пусть и с коротким простоем, чем рисковать повреждением данных одновременной работой двух версий.
:::

```yaml
spec:
  strategy:
    type: Recreate
```

`Recreate` гасит **все** старые Pod и только потом создаёт новые — с гарантированным простоем на время перехода. Применяется редко и осознанно: например, если приложение **не может** работать в двух версиях одновременно (несовместимый формат на общем томе, эксклюзивная блокировка ресурса) — тогда гарантированная кратковременная недоступность безопаснее, чем гонка версий.

### result
Применять на CoffeeShop API не будем — ему `Recreate` не нужен (версии совместимы друг с другом по контракту API). Это шаг «для словаря», а не для рук — но знать, когда он уместен, важно для собеседований и реальных задач со StatefulSet (сессия 6.5).

### why
Самая частая ошибка — ставить `Recreate` «на всякий случай» там, где подходит `RollingUpdate`, и терять обновление без простоя без необходимости. Используй `Recreate` только когда есть **конкретная** причина несовместимости версий, а не из общей осторожности.

### deep Где Recreate встречается чаще
У StatefulSet (сессия 6.5) с эксклюзивным доступом к тому (например, некоторые конфигурации баз данных, которые не допускают двух экземпляров с одним томом одновременно) или при миграции схемы БД, которая ломает совместимость со старой версией кода.

### quiz
- В каком случае `Recreate` предпочтительнее `RollingUpdate`, несмотря на простой?
- Какую гарантию даёт `RollingUpdate`, которую `Recreate` не даёт?

### links
- https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#recreate-deployment | стратегия Recreate | Kubernetes: Recreate Deployment

## 4.7 🔨 Обновление на битый образ: застряло и откат | short: 🔨 Застрявший rollout | est: ~30 мин
### intro
**Слова шага:** *застрявший rollout*, *диагностика по `rollout status` и `describe`*, *откат при частичном застревании*.

:::tip Если совсем просто
Представь, что на конвейере новая деталь не проходит контроль качества: конвейер **не рушит** уже собранные изделия — он просто не продвигается дальше, подавая сигнал «застрял здесь». Твоя задача — не паниковать и не выключать всё, а посмотреть, где именно застряло, и либо исправить, либо откатить именно эту партию.
:::

Воспроизведём реалистичную поломку: образ существует, но у него неверная команда запуска (а не просто «не существует», как в шаге 4.4 — это чуть более тонкий случай):

```bash run
kubectl set image deployment/coffeeshop-api api=coffeeshop-api:v1
kubectl patch deployment coffeeshop-api --type=json -p='[{"op":"add","path":"/spec/template/spec/containers/0/command","value":["node","/app/does-not-exist.js"]}]'
sleep 10
kubectl get pods -l app=coffeeshop-api
kubectl rollout status deployment/coffeeshop-api --timeout=15s 2>&1 | tail -3
```

### result
```out auto
```

Новый Pod переходит в `CrashLoopBackOff` (контейнер стартует, сразу падает с ошибкой «файл не найден», `kubelet` перезапускает его с нарастающей паузой — подробная таблица статусов в сессии 8.6) — **и именно поэтому** он никогда не станет `Ready`, а `maxUnavailable: 0` **не даёт** rollout продолжиться: старые Pod остаются на месте, пользователи ничего не заметили.

**Диагностика по порядку:**

```bash run
kubectl rollout status deployment/coffeeshop-api --timeout=5s 2>&1 | tail -3
kubectl get pods -l app=coffeeshop-api
newpod=$(kubectl get pods -l app=coffeeshop-api --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
kubectl describe pod "$newpod" | tail -10
```

### result
```out auto
```

`describe` нового Pod покажет в Events что-то вроде `Back-off restarting failed container` — явный сигнал «контейнер стартует и умирает», а не «не может запуститься вообще» (это была бы другая причина, например, нет ресурсов).

**Откат:**

```bash run
kubectl rollout undo deployment/coffeeshop-api
kubectl rollout status deployment/coffeeshop-api
```

### result
```out auto
```

### why
Главный урок этого шага — **не паниковать при застрявшем rollout**: `maxUnavailable: 0` работает как предохранитель, пользователи продолжают получать ответы от старых, рабочих Pod, пока ты спокойно разбираешься и откатываешь. Это прямая практическая выгода от того, что мы настроили в шаге 4.3, а не абстрактная теория.

### deep Если не получилось
- **Старые Pod тоже начали падать** — проверь, не был ли `maxUnavailable` больше нуля или не изменила ли ты что-то, что задело существующие Pod (например, общий ConfigMap, сессия 7).
- **`rollout undo` тоже «висит»** — значит, предыдущая ревизия тоже была плохой; смотри `rollout history` и указывай конкретный `--to-revision`, который точно был рабочим.

### quiz
- Почему `CrashLoopBackOff` новой версии не затронул пользователей при `maxUnavailable: 0`?
- Какая команда показывает, на каком именно этапе застрял rollout?
- Что делать, если `rollout undo` без аргументов откатывает на такую же плохую версию?

### links
- https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/ | диагностика Pod | Kubernetes: Debug Pods
- https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#checking-rollout-status | проверка статуса rollout | Kubernetes: Checking Rollout Status

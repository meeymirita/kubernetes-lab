# Сессия 10 · Автомасштабирование
dur: ~4 ч

## 10.1 Зачем автомасштабирование | short: Зачем автоскейл | est: ~20 мин
### intro
**Слова шага:** *автомасштабирование*, *scale up / scale down*, *пиковая нагрузка*, *три вида: HPA, VPA, Cluster Autoscaler*.

:::tip Если совсем просто
В час пик в кофейне открывают дополнительные кассы, а ночью оставляют одну. Держать все кассы открытыми круглосуточно — дорого, держать одну днём — очередь до улицы. Автомасштабирование — это управляющий, который сам смотрит на длину очереди и открывает или закрывает кассы, не дожидаясь, пока ты это сделаешь руками.
:::

```svg
@hpa-thermostat
```

В Kubernetes три разных «управляющих», и их легко перепутать:

| Что | Что меняет | Когда уместно |
|---|---|---|
| **HPA** (Horizontal Pod Autoscaler) | **число** Pod (реплик) | веб-сервисы без состояния — наш основной случай |
| **VPA** (Vertical Pod Autoscaler) | **размер** Pod (`requests`/`limits`) | когда нельзя запустить больше копий (БД, одиночные задачи) |
| **Cluster Autoscaler** | **число узлов** | когда Pod некуда ставить: узлы закончились |

Цепочка при росте нагрузки: HPA видит высокий CPU → добавляет Pod → Pod’ам не хватает места на узлах → Cluster Autoscaler добавляет узел. В этой лабе настоящими руками пройдём первый шаг (HPA); второй и третий разберём обзорно.

### why
Ручное `kubectl scale` из шага 4.2 не успевает за реальной нагрузкой и стоит дорого, если реплик всегда «на всякий случай» больше нужного. Автомасштабирование — это ответ на вопрос «сколько реплик нужно *сейчас*», который Kubernetes решает сам по метрике.

### quiz
- Чем HPA отличается от VPA?
- Кто отвечает за добавление *узлов*, а не Pod?

### links
- https://kubernetes.io/docs/concepts/workloads/autoscaling/ | автомасштабирование | Kubernetes: Autoscaling Workloads

## 10.2 metrics-server: откуда берутся цифры | short: metrics-server | est: ~30 мин
### intro
**Слова шага:** *`metrics-server`*, *Metrics API*, *`kubectl top`*, *`--kubelet-insecure-tls`*.

:::tip Если совсем просто
Чтобы управляющий мог судить о длине очереди, кто-то должен её считать. `metrics-server` — это человек с кликером у входа: он раз в несколько секунд обходит узлы, спрашивает у каждого «сколько CPU и памяти использует каждый Pod» и держит последние цифры. HPA ходит именно к нему. Без счётчика управляющий видит `<unknown>` и ничего не решает.
:::

В `kind` у kubelet’ов самоподписанные сертификаты, и `metrics-server` по умолчанию не доверяет им. Для учебного кластера разрешаем это флагом `--kubelet-insecure-tls` (в настоящем кластере чинят сертификаты, а не отключают проверку).

```bash run
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl patch deployment metrics-server -n kube-system --type=json \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
kubectl rollout status deployment/metrics-server -n kube-system --timeout=120s
sleep 30
kubectl top nodes
kubectl top pods
```

### result
```out auto
```

`kubectl top nodes` показывает использование CPU (в «милликорах», `250m` — четверть ядра) и памяти по каждому узлу, `top pods` — то же по Pod. Если сразу после установки видишь `error: Metrics API not available` — подожди минуту: первый сбор метрик занимает время.

### why
`metrics-server` — не система наблюдаемости (истории нет, только «сейчас»); он нужен ровно для двух потребителей: `kubectl top` и автомасштабирования. Для графиков во времени — Prometheus (сессия 11).

### deep Команды по частям
`kubectl patch … --type=json -p='[{"op":"add","path":".../args/-","value":"…"}]'` — JSON Patch: `add` с путём, оканчивающимся на `/-`, **дописывает** элемент в конец списка `args`. Версия `latest` в адресе — для учебного стенда; в настоящем кластере фиксируй конкретную версию манифеста.

### deep Если не получилось
- **`metrics-server` в `0/1 Ready`, в логе `x509: cannot validate certificate`** — флаг `--kubelet-insecure-tls` не добавился или Pod ещё не пересоздался после `patch`: `kubectl logs -n kube-system deploy/metrics-server`.
- **Нет доступа в интернет к `github.com`** — скачай `components.yaml` заранее и применяй файл локально.

### quiz
- Для чего `metrics-server` нужен кроме HPA?
- Почему в `kind` приходится добавлять `--kubelet-insecure-tls`?
- Хранит ли `metrics-server` историю метрик?

### links
- https://github.com/kubernetes-sigs/metrics-server | metrics-server | GitHub: kubernetes-sigs/metrics-server
- https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/ | конвейер метрик | Kubernetes: Resource metrics pipeline

## 10.3 HorizontalPodAutoscaler: манифест | short: HPA | est: ~40 мин
### intro
**Слова шага:** *HPA*, *`minReplicas`/`maxReplicas`*, *целевая загрузка (`averageUtilization`)*, *`resources.requests`*.

:::tip Если совсем просто
HPA — термостат. Ты задаёшь «держи загрузку около 50 %» и границы «от 2 до 6 касс». Если средняя загрузка выше — HPA добавляет Pod, ниже — убирает. Важная тонкость: «50 %» — это процент **от `requests`**, заявленных в Pod. Нет `requests` — не от чего считать, и термостат ничего не покажет.
:::

Сначала у `coffeeshop-api` должны быть `requests` на CPU. Добавим их и создадим HPA:

```bash run
kubectl patch deployment coffeeshop-api --type=strategic -p '
spec:
  template:
    spec:
      containers:
        - name: api
          resources:
            requests: {cpu: 100m, memory: 128Mi}
            limits: {memory: 256Mi}
'
kubectl rollout status deployment/coffeeshop-api
kubectl apply -f - <<'EOF'
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: {name: coffeeshop-api}
spec:
  scaleTargetRef: {apiVersion: apps/v1, kind: Deployment, name: coffeeshop-api}
  minReplicas: 2
  maxReplicas: 6
  metrics:
    - type: Resource
      resource:
        name: cpu
        target: {type: Utilization, averageUtilization: 50}
EOF
sleep 30
kubectl get hpa coffeeshop-api
```

### result
```out auto
```

Колонка `TARGETS` вида `3%/50%` — «сейчас 3 % от запрошенного CPU, цель 50 %». `REPLICAS` быстро станет равным `minReplicas` (2), даже если Deployment был с одной репликой: границу HPA поддерживает всегда. Короткая запись того же — императивная: `kubectl autoscale deployment coffeeshop-api --min=2 --max=6 --cpu-percent=50`; в проекте храним манифест, потому что он живёт в Git (шаг 2.3).

### why
Версия `autoscaling/v2` умеет много метрик сразу (CPU, память, свои метрики), и это единственный вариант, который стоит использовать; `v1` — только CPU. Формула, по которой HPA считает: `нужно реплик = ceil(текущих × (текущая метрика / целевая))` — зная её, можно предсказать поведение, не гадая.

### deep Если не получилось
- **`TARGETS` вечно `<unknown>/50%`** — это следующий шаг-поломка 10.7: нет `metrics-server` или у контейнера нет `requests.cpu`.
- **`kubectl patch` не поменял `resources`** — `name: api` в патче должно совпадать с именем контейнера в Deployment (`kubectl get deploy coffeeshop-api -o jsonpath='{.spec.template.spec.containers[*].name}'`).

### quiz
- От чего считается «50 %» в `averageUtilization`?
- Что произойдёт с числом реплик, если в Deployment их было 1, а `minReplicas: 2`?
- Чем императивный `kubectl autoscale` хуже манифеста?

### links
- https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/ | HPA | Kubernetes: Horizontal Pod Autoscaling
- https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/ | пример HPA | Kubernetes: HPA Walkthrough

## 10.4 Нагрузочный тест: смотрим, как растут реплики | short: Нагрузка и scale up/down | est: ~50 мин
### intro
**Слова шага:** *нагрузочный тест*, *`kubectl get hpa -w`*, *scale up*, *окно стабилизации (scale down)*.

:::tip Если совсем просто
Теперь устроим час пик. Запустим внутри кластера Pod, который непрерывно «стучится» в API, и будем смотреть, как термостат включает дополнительные кассы. После отбоя HPA не бросится закрывать кассы сразу — ждёт несколько минут «а вдруг толпа вернётся», чтобы не мигать.
:::

Нагрузку создаём изнутри кластера — не нужны `k6` или `hey` на Mac, достаточно `busybox`. Для живого просмотра открой **второй терминал** и выполни в нём `kubectl get hpa coffeeshop-api -w`.

```bash run
kubectl run load --image=busybox:1.36 --restart=Never -- sh -c 'while true; do for i in 1 2 3 4 5 6 7 8; do wget -q -O- http://coffeeshop-api:3000/menu >/dev/null & done; wait; done'
sleep 90
kubectl get hpa coffeeshop-api
kubectl top pods -l app=coffeeshop-api
kubectl get deploy coffeeshop-api
```

### result
```out auto
```

Загрузка выросла выше 50 %, `REPLICAS` в HPA и `READY` в Deployment поднялись выше двух (шаг по шагу, не мгновенно: HPA проверяет метрики примерно раз в 15 секунд и ограничивает скорость роста). Для сравнения — как это выглядит, если вместо `busybox` использовать `hey` или `k6` с Mac: те же запросы, но через Ingress (`http://shop.localhost/api/menu`); результат для HPA тот же, различается лишь нагрузка на сам Ingress.

Остановим нагрузку и подождём спада:

```bash run
kubectl delete pod load --now
sleep 240
kubectl get hpa coffeeshop-api
kubectl get deploy coffeeshop-api
```

### result
```out auto
```

Реплики возвращаются к `minReplicas`, но **не сразу**: для уменьшения действует окно стабилизации (по умолчанию 5 минут) — защита от «дрожания», когда нагрузка скачет вверх-вниз. Если после четырёх минут реплики ещё не упали — подожди ещё минуту и повтори `get hpa`; это не ошибка.

### why
Асимметрия сделана намеренно: наращивать быстро (иначе пользователи получат ошибки), сокращать медленно (иначе вы отдадите ресурсы за секунду до следующей волны). Тонкая настройка — поле `behavior` в HPA (скорость и окна для `scaleUp` и `scaleDown`); по умолчанию его достаточно.

### deep Если не получилось
- **Реплики не растут, CPU на `top` не превышает 50 %** — приложение слишком «лёгкое» для такой нагрузки: добавь параллельных `wget` или запусти несколько нагрузочных Pod (`load2`, `load3`).
- **Реплики выросли, но часть Pod в `Pending`** — на узлах не хватило ресурсов под `requests`; это ровно ситуация, для которой существует Cluster Autoscaler (шаг 10.6).
- **Нагрузка давит на БД, API начинает отвечать ошибками** — автомасштабирование API не масштабирует БД: узкое место переехало, это нормально и показательно.

### quiz
- Почему HPA наращивает реплики быстрее, чем сокращает?
- Что показывает колонка `TARGETS` в `kubectl get hpa`?
- Что произойдёт при росте нагрузки, если на узлах нет места под новые реплики?

### links
- https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/#algorithm-details | алгоритм HPA | Kubernetes: HPA Algorithm Details
- https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/#configurable-scaling-behavior | поведение scale up/down | Kubernetes: Configurable scaling behavior

## 10.5 VPA: размер Pod вместо числа | short: VPA (обзор) | est: ~25 мин
### intro
**Слова шага:** *VPA*, *рекомендации*, *режимы `Off`/`Initial`/`Auto`*, *конфликт с HPA*.

:::tip Если совсем просто
HPA нанимает больше кассиров. VPA вместо этого выдаёт каждому кассиру стол побольше и более быстрый компьютер. Помогает, когда добавить второго кассира нельзя: например, у базы данных одна «главная касса».
:::

VPA — не часть самого Kubernetes: он ставится отдельно (проект `kubernetes/autoscaler`) и состоит из трёх компонентов: *recommender* (смотрит историю потребления и считает подходящие `requests`), *updater* (выселяет Pod, чьи `requests` сильно отличаются от рекомендуемых) и *admission controller* (подставляет новые значения при создании Pod). Ключевое: **размер Pod нельзя изменить «на лету»** (для большинства версий) — VPA пересоздаёт Pod.

Объект выглядит так (в лабе не применяем — только читаем):

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata: {name: db}
spec:
  targetRef: {apiVersion: apps/v1, kind: Deployment, name: db}
  updatePolicy: {updateMode: "Off"}   # только рекомендации, без вмешательства
```

В режиме `Off` VPA никого не перезапускает, а лишь подсказывает в `kubectl describe vpa db`, какие `requests` стоило бы задать. Это самый безопасный способ начать: взять рекомендацию и вручную поправить манифест.

### why
**Нельзя включать HPA и VPA на одну и ту же метрику** (например, оба по CPU): один растит число Pod, другой меняет размер, и они начинают бороться. Допустимо: HPA по CPU + VPA в режиме `Off` как подсказчик; или HPA по своей метрике (число запросов) + VPA по CPU и памяти.

### quiz
- Почему VPA нельзя совмещать с HPA на одну метрику?
- Что делает режим `updateMode: "Off"`?
- Что приходится делать с Pod, чтобы изменить его размер?

### links
- https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler | VPA | GitHub: kubernetes/autoscaler (VPA)
- https://kubernetes.io/docs/concepts/workloads/autoscaling/vertical-pod-autoscale/ | VPA в документации | Kubernetes: Vertical Pod Autoscaling

## 10.6 Cluster Autoscaler: почему в kind не запустить | short: Cluster Autoscaler | est: ~20 мин
### intro
**Слова шага:** *Cluster Autoscaler*, *облачный провайдер*, *Pod в `Pending` из-за нехватки ресурсов*, *Karpenter (обзор)*.

:::tip Если совсем просто
Когда все кассы заняты, а очередь растёт, HPA «нанимает» кассиров, но в зале больше нет столов. Cluster Autoscaler — тот, кто звонит арендодателю и берёт ещё одно помещение. Чтобы позвонить, нужен телефон арендодателя — API облака. У `kind` «облако» — это просто Docker на твоём Mac, и звонить некому.
:::

Cluster Autoscaler следит за Pod в статусе `Pending` с причиной «не хватает ресурсов» и просит у облачного провайдера (AWS, GCP, Azure, Yandex Cloud…) новый виртуальный узел; в обратную сторону — удаляет узлы, которые долго простаивают. Всё это работает через API облака, которого в `kind` нет. Поэтому здесь это **только объяснение**: в управляемом кластере (EKS/GKE/AKS/Yandex Managed Kubernetes) включается галочкой в настройках группы узлов — задаёшь минимум и максимум узлов, и дальше всё идёт автоматически. Альтернатива — Karpenter: не «группы узлов фиксированного размера», а подбор подходящего типа машины под конкретные ожидающие Pod.

Что можно проверить прямо сейчас — то, на что он реагирует:

```bash run
kubectl run too-big --image=busybox:1.36 --restart=Never --overrides='{"spec":{"containers":[{"name":"c","image":"busybox:1.36","command":["sleep","60"],"resources":{"requests":{"cpu":"1000"}}}]}}'
sleep 5
kubectl get pod too-big
kubectl describe pod too-big | grep -A3 Events
kubectl delete pod too-big --now
```

### result
```out auto
```

Pod застрял в `Pending`, а в событиях — `FailedScheduling … Insufficient cpu`. Именно такое событие — сигнал для Cluster Autoscaler «нужен ещё узел». В нашем `kind` никто на сигнал не отреагирует, поэтому Pod так и останется ждать.

### why
Три автоскейлера образуют цепочку: HPA добавляет Pod → при нехватке места Pod ждёт в `Pending` → Cluster Autoscaler добавляет узел → Pod запускается. Если в цепочке нет третьего звена, то HPA упрётся в ёмкость кластера: проверяй `maxReplicas` с учётом того, сколько реплик реально поместится.

### quiz
- Какое состояние Pod служит сигналом для Cluster Autoscaler?
- Почему Cluster Autoscaler нельзя запустить в `kind`?
- Что произойдёт с HPA, если узлов не хватает для новых реплик?

### links
- https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler | Cluster Autoscaler | GitHub: kubernetes/autoscaler (Cluster Autoscaler)
- https://karpenter.sh/ | Karpenter | Karpenter

## 10.7 🔨 HPA показывает `<unknown>` | short: 🔨 HPA unknown | est: ~35 мин
### intro
**Слова шага:** *`<unknown>` в TARGETS*, *`FailedGetResourceMetric`*, *`missing request for cpu`*.

:::tip Если совсем просто
Термостат повесили, а он показывает прочерк вместо температуры. Либо у него нет датчика (`metrics-server`), либо в комнате нет эталона «норма» (`requests`). Два разных случая выглядят одинаково — и различаются только текстом в событиях.
:::

Сломаем вторым способом — уберём у Deployment `requests` и посмотрим:

```bash run
kubectl create deployment norequests --image=nginx:alpine
kubectl autoscale deployment norequests --min=1 --max=3 --cpu-percent=50
sleep 40
kubectl get hpa norequests
kubectl describe hpa norequests | grep -B1 -A3 -i 'ScalingActive\|FailedGet'
```

### result
```out auto
```

`TARGETS` — `<unknown>/50%`, а в условиях: `ScalingActive False … failed to get cpu utilization: missing request for cpu`. Чиним: добавляем `requests` и ждём, пока HPA получит цифры:

```bash run
kubectl set resources deployment norequests --requests=cpu=50m
sleep 45
kubectl get hpa norequests
```

### result
```out auto
```

Теперь вместо `<unknown>` — процент. Если же `<unknown>` даже при корректных `requests` — проверь первую причину: `kubectl top pods` не работает → `metrics-server` не установлен или не готов (шаг 10.2). Убираем за собой:

```bash run
kubectl delete hpa norequests
kubectl delete deployment norequests
```

**Приёмка сессии:** нагрузка на API → реплики растут сами (шаг 10.4), после снятия нагрузки падают обратно до `minReplicas`; HPA в `kubectl get hpa coffeeshop-api` показывает числовой `TARGETS`, а не `<unknown>`.

### why
Порядок поиска причины `<unknown>`: сначала `kubectl top pods` (есть ли вообще метрики), затем `describe hpa` (текст условия называет причину), затем `requests` у контейнеров (у **каждого** контейнера Pod, включая sidecar — достаточно одного без `requests`, чтобы всё сломалось).

### deep Если не получилось
- **После `set resources` всё ещё `<unknown>`** — Pod ещё не пересоздан или метрики по нему ещё не собраны; подожди минуту и перепроверь.

### quiz
- Какие две причины дают `<unknown>` в `TARGETS` и как отличить одну от другой?
- Почему достаточно одного контейнера без `requests`, чтобы сломать HPA по CPU?

### links
- https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/#support-for-resource-metrics | метрики ресурсов | Kubernetes: HPA resource metrics

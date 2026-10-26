# Сессия 11 · Наблюдаемость
dur: ~4 ч

## 11.1 Зачем наблюдаемость в кластере | short: Зачем наблюдаемость | est: ~20 мин
### intro
**Слова шага:** *метрики*, *логи*, *события*, *наблюдаемость (observability)*, *pull-модель*.

:::tip Если совсем просто
У автомобиля есть приборная панель: скорость, обороты, температура — не нужно открывать капот на каждой кочке, чтобы понять, что всё в порядке. До сих пор мы в кластере именно «открывали капот»: `kubectl exec`, `kubectl describe`. Наблюдаемость — это приборная панель: цифры и графики собираются сами, а капот открываешь, только когда лампочка загорелась.
:::

```svg
@metrics-flow
```

Три источника правды о работающей системе:

| Что | Вопрос, на который отвечает | Чем смотрим в этой сессии |
|---|---|---|
| **Метрики** — числа во времени | «Сколько? Как быстро? Растёт ли?» | Prometheus + Grafana |
| **Логи** — строки событий | «Что именно произошло в этот момент?» | `kubectl logs`, обзор агрегаторов |
| **События** — объекты Kubernetes | «Что кластер сделал с моим Pod?» | `kubectl get events` |

Prometheus работает по **pull-модели**: сам ходит за цифрами по HTTP к каждому «источнику» по расписанию (обычно раз в 15–30 секунд). Приложение ничего никуда не отправляет — оно лишь открывает страницу `/metrics`, а кто, куда и как часто ходит, решает Prometheus.

### why
Без метрик вы узнаёте о проблеме от пользователей, и причину ищете вслепую. С метриками видно *тенденцию* («память растёт уже три часа») и можно настроить оповещение до аварии. Автомасштабирование из сессии 10 решает «что делать с нагрузкой», наблюдаемость — «как понять, что с системой происходит».

### quiz
- Чем метрики отличаются от логов?
- Что значит «pull-модель» у Prometheus?

### links
- https://prometheus.io/docs/introduction/overview/ | обзор Prometheus | Prometheus: Overview

## 11.2 kubectl top: быстрый взгляд | short: kubectl top | est: ~15 мин
### intro
**Слова шага:** *`kubectl top`*, *`--containers`*, *`--sort-by`*.

:::tip Если совсем просто
`kubectl top` — взгляд на стрелку спидометра прямо сейчас. Удобно, быстро, но у него нет памяти: что было вчера, он не знает. Для «что было вчера» нужен Prometheus.
:::

`kubectl top` берёт данные из `metrics-server`, установленного в шаге 10.2 (без него будет `Metrics API not available`):

```bash run
kubectl top nodes
kubectl top pods -A --sort-by=memory | head -8
kubectl top pods --containers -l app=coffeeshop-api
```

### result
```out auto
```

`--sort-by=memory` (или `cpu`) выводит наверх самые «прожорливые» Pod; `--containers` разбивает Pod на контейнеры (полезно, когда рядом с приложением работает sidecar). Сравни `top` с `requests`/`limits` из шага 8.3: Pod, у которого память уже близка к `limits`, — кандидат на `OOMKilled`.

### why
Это первая команда при жалобе «всё тормозит»: за 5 секунд видно, не упёрлись ли узлы или конкретный Pod в ресурсы. Но это *снимок*: пиковая нагрузка 10 минут назад здесь не видна.

### quiz
- Откуда `kubectl top` берёт данные и что будет, если этого компонента нет?
- Чем `top` хуже Prometheus для разбора вчерашнего инцидента?

### links
- https://kubernetes.io/docs/reference/kubectl/generated/kubectl_top/ | kubectl top | Kubernetes: kubectl top

## 11.3 Prometheus и Grafana через Helm | short: kube-prometheus-stack | est: ~45 мин
### intro
**Слова шага:** *`kube-prometheus-stack`*, *Prometheus Operator*, *Alertmanager*, *`node-exporter`*, *`kube-state-metrics`*, *namespace `monitoring`*.

:::tip Если совсем просто
Собирать приборную панель из отдельных датчиков долго. `kube-prometheus-stack` — готовый комплект «приборная панель в сборе»: в коробке и Prometheus (собирает цифры), и Grafana (рисует графики), и Alertmanager (звонит, если что-то горит), и датчики для самого кластера. Ставится одной командой Helm (подробно Helm — сессия 12; сейчас используем его как установщик, как с Traefik в шаге 5.4).
:::

Комплект тяжёлый (несколько Pod, сотни мегабайт). Для учебного стенда выключаем лишнее и храним данные недолго:

```bash run
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --set grafana.adminPassword=admin \
  --set prometheus.prometheusSpec.retention=6h \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
  --set alertmanager.enabled=false \
  --wait --timeout 8m
kubectl get pods -n monitoring
```

### result
```out auto
```

Что запущено: **Prometheus** (хранилище и сборщик), **Grafana** (графики), **Prometheus Operator** (следит за объектами `ServiceMonitor`/`PodMonitor` и настраивает Prometheus по ним), **kube-state-metrics** (метрики о *состоянии объектов*: «сколько реплик заказано и сколько готово»), **node-exporter** (метрики самих узлов: диск, сеть, процессор). Параметр `serviceMonitorSelectorNilUsesHelmValues=false` разрешает Prometheus подхватывать `ServiceMonitor` из **любых** namespace без специальной метки — иначе следующий шаг пришлось бы дополнять ярлыками. Пароль `admin` — только для учебного стенда.

Открываем интерфейсы с Mac (в двух терминалах или с `&` в фоне):

```bash run
kubectl port-forward -n monitoring svc/monitoring-grafana 3001:80 >/dev/null 2>&1 &
kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-prometheus 9090:9090 >/dev/null 2>&1 &
sleep 3
curl -s -o /dev/null -w 'grafana: HTTP %{http_code}\n' http://localhost:3001/login
curl -s -o /dev/null -w 'prometheus: HTTP %{http_code}\n' http://localhost:9090/-/ready
```

### result
```out auto
```

Grafana — в браузере `http://localhost:3001` (логин `admin`, пароль `admin`), Prometheus — `http://localhost:9090`. Остановить проброс: `kill %1 %2` (или закрыть терминал).

### why
Именно через готовый chart и принято ставить мониторинг: ручная сборка десятка компонентов и их связей — слишком много работы ради «стандартного» результата. А Prometheus Operator добавляет *декларативность*: вместо правки конфига Prometheus вы создаёте объекты `ServiceMonitor` — как `Ingress` для Traefik.

### deep Если не получилось
- **`helm install` по таймауту `--wait`** — часть образов качается долго; проверь `kubectl get pods -n monitoring`, пока не все `Running`, и повторяй `helm status monitoring -n monitoring`. Если не хватает памяти Docker Desktop — увеличь лимит (рекомендуется 6 ГБ и выше).
- **Имена сервисов не совпали** — `kubectl get svc -n monitoring` покажет точные имена; первая часть — имя релиза (`monitoring`).

### quiz
- За что отвечает каждый из компонентов: Prometheus, Grafana, kube-state-metrics, node-exporter?
- Что позволяет делать Prometheus Operator?
- Почему мы ставим мониторинг готовым chart’ом, а не вручную?

### links
- https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack | chart | GitHub: kube-prometheus-stack
- https://prometheus-operator.dev/ | Prometheus Operator | Prometheus Operator

## 11.4 ServiceMonitor: как Prometheus узнаёт, что опрашивать | short: ServiceMonitor | est: ~40 мин
### intro
**Слова шага:** *`ServiceMonitor`*, *`PodMonitor`*, *CRD*, *endpoint `/metrics`*, *`selector`*.

:::tip Если совсем просто
Prometheus — обходчик с блокнотом, но по умолчанию он не знает, в какие двери стучать. `ServiceMonitor` — записка обходчику: «заходи в сервисы с такой-то табличкой (`label`), на такой-то порт, в раздел `/metrics`». Новая дверь с табличкой появилась — обходчик пойдёт и туда без ручной настройки.
:::

Наш API CoffeeShop свою страницу `/metrics` не публикует (код приложения в этой лабе не меняется), поэтому покажем механизм на компоненте, который её публикует **сам** — Traefik (шаг 5.4). Включим его метрики и `ServiceMonitor` через значения chart’а:

```bash run
helm show values traefik/traefik | grep -n -A6 'prometheus:' | head -24
helm upgrade traefik traefik/traefik --namespace traefik --reuse-values \
  --set metrics.prometheus.service.enabled=true \
  --set metrics.prometheus.serviceMonitor.enabled=true
kubectl rollout status deployment/traefik -n traefik --timeout=120s
kubectl get servicemonitor -A
```

### result
```out auto
```

`helm show values` нужен, чтобы **сверить имена ключей** с версией chart’а, которую ты поставила: в разных версиях они меняются. Появился объект `ServiceMonitor` в namespace `traefik`. Через минуту в интерфейсе Prometheus (`http://localhost:9090/targets`) должна появиться цель `serviceMonitor/traefik/…` в состоянии `UP`. Проверим из командной строки и сделаем свой запрос:

```bash run
sleep 45
curl -s 'http://localhost:9090/api/v1/query?query=up%7Bnamespace%3D%22traefik%22%7D' | head -c 400; echo
curl -s 'http://localhost:9090/api/v1/query?query=sum(traefik_service_requests_total)' | head -c 300; echo
```

### result
```out auto
```

Значение `up` равное `1` — «цель отвечает». Метрика `traefik_service_requests_total` — счётчик запросов, прошедших через Traefik: как раз то, что нужно для графика «запросы в секунду» (в Prometheus — `rate(...)`). Если для API понадобятся собственные метрики, цепочка такая: приложение отдаёт `/metrics` (в Node.js — библиотека `prom-client`) → `Service` с именованным портом → `ServiceMonitor` с тем же `selector.matchLabels`.

### why
`ServiceMonitor` — это тот же принцип, что `Ingress` (шаг 5.4): вы описываете *желаемое* («опрашивать вот это»), а оператор переводит это в конфиг Prometheus. Метки на `Service` — единственный «клей» между ними; поэтому опечатка в `selector` приводит к молчаливому «цель не найдена» — это и будет поломкой шага 11.7.

### deep ServiceMonitor вручную
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata: {name: coffeeshop-api}
spec:
  selector:
    matchLabels: {app: coffeeshop-api}   # метка Service, не Pod
  endpoints:
    - port: http          # ИМЯ порта в Service, не номер
      path: /metrics
      interval: 30s
```
Два частых промаха: у порта в `Service` нет `name`, и метка в `selector` — не метка `Service` (а метка Pod).

### deep Если не получилось
- **`unknown flag`/ключ не найден в chart** — другая версия chart’а: открой `helm show values traefik/traefik` и найди раздел `metrics.prometheus`.
- **В `targets` пусто** — подожди минуту (оператор перенастраивает Prometheus), затем проверь, что `kubectl get servicemonitor -A` не пуст.

### quiz
- Что связывает `ServiceMonitor` с нужным `Service` — метки или имя?
- Что должно быть у порта в `Service`, чтобы `ServiceMonitor` мог на него сослаться?
- Что должно сделать приложение, чтобы его можно было мониторить Prometheus’ом?

### links
- https://prometheus-operator.dev/docs/developer/getting-started/ | ServiceMonitor | Prometheus Operator: Getting Started
- https://doc.traefik.io/traefik/observe/metrics/ | метрики Traefik | Traefik: Metrics

## 11.5 Grafana: дашборд для CoffeeShop | short: Grafana | est: ~45 мин
### intro
**Слова шага:** *Grafana*, *источник данных (datasource)*, *дашборд*, *панель*, *PromQL*.

:::tip Если совсем просто
Prometheus хранит числа, но смотреть на таблицы чисел неудобно. Grafana — монитор в диспетчерской: рисует из тех же чисел графики. Datasource — кабель, которым монитор подключён к Prometheus. Дашборд — раскладка экрана; панель — один график.
:::

Chart уже подключил Prometheus как источник данных и положил дашборды для кластера (`Kubernetes / Compute Resources / Pod` и др.). Посмотрим и сделаем свой. Сначала готовые числа для API — те запросы PromQL, которые пойдут в панели:

```bash run
Q() { curl -s -G 'http://localhost:9090/api/v1/query' --data-urlencode "query=$1" | head -c 350; echo; }
echo "CPU API (ядра):";  Q 'sum(rate(container_cpu_usage_seconds_total{pod=~"coffeeshop-api-.*",container="api"}[2m]))'
echo "Память API (байты):"; Q 'sum(container_memory_working_set_bytes{pod=~"coffeeshop-api-.*",container="api"})'
echo "Готовых реплик API:"; Q 'kube_deployment_status_replicas_ready{deployment="coffeeshop-api"}'
echo "Перезапуски:"; Q 'sum(kube_pod_container_status_restarts_total{pod=~"coffeeshop-api-.*"})'
```

### result
```out auto
```

Все четыре запроса возвращают число — значит, датчики кластера (cAdvisor внутри kubelet и `kube-state-metrics`) уже дают всё нужное без изменений в приложении. Теперь в Grafana (`http://localhost:3001`, `admin`/`admin`):

1. Меню → **Dashboards** → **New** → **New dashboard** → **Add visualization**, источник — `Prometheus`.
2. Вставь запрос про CPU в поле запроса, в правом столбце задай название «CPU API», единицу (`Unit`) — *Misc → short* или просто оставь число. Нажми **Apply**.
3. Повтори для памяти (единица **Data → bytes**) и числа готовых реплик (тип панели **Stat**).
4. Сохрани (**Save dashboard**), назови «CoffeeShop».
5. Запусти нагрузку из шага 10.4 и посмотри, как реплики и CPU растут на графиках.

### why
Один раз собранный дашборд отвечает на «как API себя чувствует» за секунды, без `kubectl`. Три панели — минимальный набор «золотых сигналов» для сервиса без собственных метрик: нагрузка (CPU), ёмкость (память), здоровье (готовые реплики и перезапуски). Когда приложение начнёт отдавать свои метрики, к ним добавятся запросы и задержка (RPS, p95).

### deep Команды по частям
`rate(counter[2m])` превращает счётчик, который только растёт, в скорость «в секунду» за окно 2 минуты — без `rate` график счётчика бесполезен. `sum(...)` складывает значения всех реплик в одну линию; без него будет по линии на Pod. `pod=~"coffeeshop-api-.*"` — регулярное выражение по метке `pod`.

### deep Если не получилось
- **Панель пуста («No data»)** — это поломка шага 11.7: проверь выбранный источник данных, диапазон времени (правый верхний угол — «Last 15 minutes») и точные значения меток.

### quiz
- Что такое datasource в Grafana?
- Зачем нужна функция `rate()` для счётчика?
- Какие метрики API доступны без изменения приложения и откуда они берутся?

### links
- https://grafana.com/docs/grafana/latest/getting-started/build-first-dashboard/ | первый дашборд | Grafana: Build your first dashboard
- https://prometheus.io/docs/prometheus/latest/querying/basics/ | PromQL | Prometheus: Querying basics

## 11.6 Логи: kubectl logs и агрегаторы | short: Логи | est: ~30 мин
### intro
**Слова шага:** *`kubectl logs`*, *`--previous`*, *`--since`*, *`-l` (по метке)*, *агрегатор логов*.

:::tip Если совсем просто
Логи — бортовой журнал каждого Pod. Пока Pod один, достаточно открыть его журнал. Когда их десять и они то умирают, то рождаются, листать десять журналов неудобно — нужен архивариус, который собирает все журналы в одну папку и позволяет искать по ней.
:::

```bash run
kubectl logs deploy/coffeeshop-api --tail=5
kubectl logs -l app=coffeeshop-api --tail=2 --prefix
kubectl logs deploy/coffeeshop-api --since=2m | wc -l
kubectl delete pod -l app=coffeeshop-api --wait=false
sleep 15
kubectl logs deploy/coffeeshop-api --tail=2
```

### result
```out auto
```

`--tail=N` — последние N строк, `--since=2m` — за последние две минуты, `-l app=…` — по метке со **всех** реплик сразу, `--prefix` — подписывает строку именем Pod (иначе не поймёшь, чья она). Для упавшего контейнера: `kubectl logs <pod> --previous` — журнал **предыдущего** запуска (текущий пуст, потому что контейнер только стартовал).

Главное ограничение: `kubectl logs` читает файлы на узле. Когда Pod удалён, его логи исчезают. Поэтому в настоящем кластере ставят **агрегатор**:

| Решение | Идея |
|---|---|
| **Loki + Promtail/Alloy** | хранит логи, индексирует только метки (как Prometheus), смотрим в той же Grafana |
| **EFK** (Elasticsearch + Fluent Bit + Kibana) | полнотекстовый поиск, тяжелее и дороже |
| **Облачный сервис** (CloudWatch, Cloud Logging, Yandex Cloud Logging) | в управляемом кластере уже подключён |

В лабе агрегатор не ставим: принцип тот же, что и в метриках (агент на каждом узле читает файлы логов и отправляет в хранилище), а ставится он ещё одним Helm-chart’ом (`grafana/loki`).

### why
Логи нужны именно *после* инцидента: Pod, который падал вчера, уже пересоздан, и `kubectl logs` покажет чистый новый запуск. Правило: приложение пишет логи в **stdout/stderr** (а не в файл внутри контейнера) — тогда и `kubectl logs`, и любой агрегатор их увидят без дополнительной настройки.

### deep Если не получилось
- **`Error from server (BadRequest): container … is waiting to start`** — Pod ещё в `ContainerCreating`: логов нет, смотри `describe pod`.
- **Несколько контейнеров в Pod** — `kubectl logs <pod> -c <имя контейнера>`.

### quiz
- Как посмотреть логи контейнера, который только что упал и перезапустился?
- Почему `kubectl logs` не годится как единственное средство в продакшне?
- Куда приложение должно писать логи, чтобы кластер их собрал?

### links
- https://kubernetes.io/docs/concepts/cluster-administration/logging/ | логирование | Kubernetes: Logging Architecture
- https://grafana.com/docs/loki/latest/ | Loki | Grafana Loki

## 11.7 🔨 Метрика есть, а на дашборде пусто | short: 🔨 Пустой дашборд | est: ~40 мин
### intro
**Слова шага:** *`No data`*, *метки в запросе*, *диапазон времени*, *`targets` в Prometheus*.

:::tip Если совсем просто
Приборная панель горит чёрным: то ли датчик сломан, то ли ты смотришь не на ту стрелку, то ли «часы» показывают вчерашний день. Три разных причины — три разных места, куда смотреть.
:::

Сломаем запрос опечаткой в метке — самой частой причиной «No data»:

```bash run
Q() { curl -s -G 'http://localhost:9090/api/v1/query' --data-urlencode "query=$1" | head -c 300; echo; }
echo "запрос с опечаткой (coffeeshop-apii):"; Q 'sum(kube_deployment_status_replicas_ready{deployment="coffeeshop-apii"})'
echo "метрика существует вообще?:"; Q 'count(kube_deployment_status_replicas_ready)'
echo "какие значения у метки deployment:"; curl -s 'http://localhost:9090/api/v1/label/deployment/values' | head -c 300; echo
echo "исправленный запрос:"; Q 'sum(kube_deployment_status_replicas_ready{deployment="coffeeshop-api"})'
```

### result
```out auto
```

Первый запрос возвращает **пустой список** (`"result":[]`) — не ошибку, а «ничего не подошло под условия». Второй показывает, что метрика в Prometheus есть. Третий перечисляет настоящие значения метки — и среди них нет `coffeeshop-apii`. Чиним опечатку — данные появляются. Порядок поиска, когда панель пуста:

1. **Диапазон времени** в Grafana (правый верхний угол): если «Last 5 minutes», а метрика появилась позже или вы смотрите на старое — пусто.
2. **Источник данных панели** — выбран `Prometheus`, а не пустой/другой.
3. **Метрика существует?** Запрос без фильтров (`count(имя_метрики)`) — если пусто, проблема *до* Grafana: цель не опрашивается (`/targets`), `ServiceMonitor` не подхватился (метка в `selector`, имя порта).
4. **Фильтры меток** (`namespace`, `pod`, `deployment`): сверь с `label/<имя>/values`, как выше.
5. **Единицы и функции**: `rate()` на gauge или без `[окна]` тоже даёт пустоту или нули.

**Приёмка сессии:** на дашборде «CoffeeShop» видны CPU, память и число реплик API, а логи — через `kubectl logs -l app=coffeeshop-api --prefix`; для просмотра не потребовалось ни одного `kubectl exec`.

Убираем проброс портов (мониторинг оставляем для сессий 12–15 по желанию; удалить — `helm uninstall monitoring -n monitoring`, это заметно освободит память):

```bash run
kill %1 %2 2>/dev/null; true
kubectl get pods -n monitoring --no-headers | wc -l
```

### result
```out auto
```

### why
Пустой график страшнее красного: красный сразу говорит «проблема», а пустой может значить и «всё хорошо», и «датчик не подключён». Поэтому в продакшне настраивают оповещение на *отсутствие данных* (`absent()` в PromQL) — молчание метрики тоже авария.

### deep Если не получилось
- **Метрика есть в Prometheus, на дашборде нет** — почти всегда дело в источнике данных панели или переменных дашборда (`$namespace`, `$pod`): они ограничивают выборку.

### quiz
- В каком порядке проверять причины пустой панели Grafana?
- Чем пустой ответ запроса отличается от ошибки запроса?
- Зачем ставить оповещение на пропажу метрики?

### links
- https://prometheus.io/docs/prometheus/latest/querying/functions/#absent | absent() | Prometheus: absent()

# Сессия 6 · Хранение данных
dur: ~4 ч

## 6.1 Временные и постоянные данные | short: emptyDir и hostPath | est: ~25 мин
### intro
**Слова шага:** *Volume*, *`emptyDir`*, *`hostPath`*.

:::tip Если совсем просто
`emptyDir` — это блокнот, который выдают на время встречи и забирают на выходе: пока встреча идёт (Pod жив), в нём можно писать и несколько участников (контейнеры одного Pod) могут делиться одним блокнотом, но как только встреча закончилась — блокнот выбросили. Для базы данных это неприемлемо: данные обязаны переживать встречу.
:::

```yaml
spec:
  containers:
    - name: api
      volumeMounts:
        - name: cache
          mountPath: /tmp/cache
  volumes:
    - name: cache
      emptyDir: {}
```

**`emptyDir`** — временный том, создаётся пустым при старте Pod и **удаляется навсегда**, когда Pod покидает узел (не только при пересоздании — даже при простом перезапуске контейнера внутри того же Pod том может сохраниться, но при удалении самого Pod — не сохраняется). Годится для кэша, временных файлов, обмена данными между контейнерами одного Pod — не для БД.

**`hostPath`** — монтирует каталог **с диска самого узла**. Выглядит как решение («данные ведь останутся на диске узла!»), но на практике — ловушка: Pod может быть пересоздан на **другом** узле (sheduler не обязан вернуть его на тот же), и тогда данные останутся там, где их больше никто не найдёт. `hostPath` уместен для узкого круга системных задач (доступ к `docker.sock`, логам самого узла), но не для данных приложения.

### result
Запускать не будем — это шаг-предупреждение, настоящее решение для PostgreSQL — PersistentVolume/PersistentVolumeClaim в следующих шагах.

### why
Самая частая ошибка новичков — поставить `hostPath` под базу данных, порадоваться, что «данные переживают перезапуск Pod», и потерять их при первом же переносе Pod на другой узел или при масштабировании кластера. Правильный инструмент для «данные должны жить независимо от конкретного Pod и узла» — PersistentVolume.

### deep Если не получилось понять разницу
Задай себе вопрос: «переживут ли данные, если Pod переедет на другой физический/виртуальный узел?» Для `emptyDir` и `hostPath` ответ «нет» (данные либо исчезнут вовсе, либо останутся на узле, с которого Pod уже уехал). Для PersistentVolume — «да», это и есть его единственная работа.

### quiz
- Что происходит с `emptyDir`, когда Pod удаляется?
- Почему `hostPath` — ловушка для данных приложения, даже если кажется, что «данные на диске, значит в безопасности»?
- Для каких задач `hostPath` всё же уместен?

### links
- https://kubernetes.io/docs/concepts/storage/volumes/#emptydir | emptyDir | Kubernetes: emptyDir
- https://kubernetes.io/docs/concepts/storage/volumes/#hostpath | hostPath | Kubernetes: hostPath

## 6.2 PV, PVC, StorageClass | short: PV и PVC | est: ~40 мин
### intro
**Слова шага:** *PersistentVolume (PV)*, *PersistentVolumeClaim (PVC)*, *StorageClass*, *динамический провижининг*, *`accessModes`*.

:::tip Если совсем просто
PersistentVolume — это реальная **съёмная флешка** (кусок диска). PersistentVolumeClaim — твоя **заявка** «нужна флешка не меньше 1 ГБ» (ты не выбираешь физически конкретную флешку — заявку удовлетворяет первая подходящая). StorageClass — это **автомат, который сам нарезает новую флешку по заявке**, если готовых подходящего размера нет (динамический провижининг — обычный путь, ручной подбор существующих PV — редкость для учебных целей).
:::

```svg
@pvc-survives-pod
```

Три уровня:

- **PersistentVolume (PV)** — реальный ресурс хранения (кусок диска, сетевое хранилище). В `kind` их обычно не создают руками — они появляются автоматически (см. ниже).
- **PersistentVolumeClaim (PVC)** — твой **запрос**: сколько места, какой `accessMode` (`ReadWriteOnce` — один узел пишет; `ReadWriteMany` — несколько узлов одновременно, нужна особая поддержка хранилища; `ReadOnlyMany`). PVC привязывается (*bind*) к подходящему PV.
- **StorageClass** — «рецепт», по которому **динамически** создаётся новый PV под конкретный PVC, если готового нет. В `kind` по умолчанию есть StorageClass `standard` (провайдер `rancher.io/local-path`), который создаёт PV прямо из каталога на диске узла — достаточно для учебных целей, хотя и привязывает PV к конкретному узлу.

```bash run
kubectl get storageclass
cat > manifests/05-pvc-db.yaml <<'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: db-data
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 1Gi
EOF
kubectl apply -f manifests/05-pvc-db.yaml
kubectl get pvc db-data
kubectl get pv
```

### result
```out auto
```

PVC без явного `storageClassName` берёт **StorageClass по умолчанию** (помечен `(default)` в `kubectl get storageclass`) — это и запустило динамический провижининг: StorageClass создал новый PV, и PVC сразу перешёл в статус `Bound`.

### why
Разделение «запрос» (PVC, в манифестах приложения) и «реальный ресурс» (PV, управляется инфраструктурой/облаком) позволяет командам приложений не знать деталей конкретного хранилища (сетевой диск AWS EBS, Google PD, локальный путь) — везде один и тот же PVC-манифест, меняется только StorageClass под капотом.

### deep Если не получилось
- **PVC навечно в `Pending`** — почти всегда нет подходящего StorageClass по умолчанию или запрошенный `storageClassName` не существует (полный разбор — 🔨-шаг 6.7).
- **`kubectl get pv` показывает PV не той ёмкости** — провайдер `local-path` в `kind` может выделить чуть больше запрошенного (округление до блока диска) — это нормально.

### quiz
- Чем PersistentVolume отличается от PersistentVolumeClaim по тому, кто его создаёт?
- Что делает StorageClass при динамическом провижининге?
- Что означает `accessMode: ReadWriteOnce`?

### links
- https://kubernetes.io/docs/concepts/storage/persistent-volumes/ | PersistentVolume | Kubernetes: Persistent Volumes
- https://kubernetes.io/docs/concepts/storage/storage-classes/ | StorageClass | Kubernetes: Storage Classes

## 6.3 PostgreSQL 18 в кластере | short: PostgreSQL в Pod | est: ~35 мин
### intro
**Слова шага:** *том PostgreSQL*, *`PGDATA`*, *переменные окружения образа*.

:::tip Если совсем просто
Это тот же PostgreSQL 18, что крутился в Compose в Docker-/Traefik-лабах — переезжает «мебель», а не меняется «квартирант». Главное отличие: вместо `volumes:` в `compose.yaml` — `volumeMounts`/`volumes` в манифесте, ссылающиеся на наш PVC.
:::

```bash run
cat > manifests/06-deployment-db.yaml <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: db
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels: {app: db}
  template:
    metadata:
      labels: {app: db}
    spec:
      containers:
        - name: postgres
          image: postgres:18
          env:
            - name: POSTGRES_DB
              value: coffeeshop
            - name: POSTGRES_USER
              value: coffeeshop
            - name: POSTGRES_PASSWORD
              value: temporary-plaintext-password
            - name: PGDATA
              value: /var/lib/postgresql/data/pgdata
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql
          ports:
            - containerPort: 5432
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: db-data
---
apiVersion: v1
kind: Service
metadata:
  name: db
spec:
  selector: {app: db}
  ports:
    - port: 5432
      targetPort: 5432
EOF
kubectl apply -f manifests/06-deployment-db.yaml
kubectl wait --for=condition=Available deployment/db --timeout=60s
```

### result
```out auto
```

Три детали, которые легко упустить:

- **`strategy: Recreate`** — не случайно: PostgreSQL с одной репликой **не умеет** работать в двух экземплярах одновременно с одним томом (`ReadWriteOnce` — только один писатель); `RollingUpdate` попытался бы на мгновение поднять вторую копию рядом со старой и столкнулся бы с блокировкой файлов данных. Это ровно пример из шага 4.6.
- **`mountPath: /var/lib/postgresql`** (не `/var/lib/postgresql/data`) — том монтируется выше, а сам PostgreSQL кладёт данные в подкаталог `PGDATA` — такое же соглашение, как зафиксировано для всего сайта (решение владельца от 03.10: том монтируется в `/var/lib/postgresql`, не в `/data`).
- Пароль в переменной окружения открытым текстом — временно, для первого запуска; сессия 7.3 переносит его в Secret.

### why
Перенос stateful-сервиса — ровно тот случай, где различие между Deployment-без-тома (сессия 3–4) и Deployment-с-PVC становится ощутимым: без PVC первый же пересозданный Pod БД означал бы потерю всех данных.

### deep Если не получилось
- **PostgreSQL падает с `PANIC: could not open file`** — скорее всего PVC был создан **до** смены `PGDATA` и в нём остались файлы от предыдущей попытки с другим путём; для учебного стенда проще удалить PVC и создать заново (`kubectl delete pvc db-data`, данные тестовые).

### quiz
- Почему для PostgreSQL в этой лабе выбрана стратегия `Recreate`, а не `RollingUpdate`?
- Куда реально попадают файлы базы данных при `mountPath: /var/lib/postgresql` и `PGDATA=/var/lib/postgresql/data/pgdata`?

### links
- https://hub.docker.com/_/postgres | официальный образ PostgreSQL | Docker Hub: postgres
- https://kubernetes.io/docs/concepts/storage/volumes/#persistentvolumeclaim | монтирование PVC в Pod | Kubernetes: persistentVolumeClaim

## 6.4 Данные переживают пересоздание Pod | short: Проверка устойчивости | est: ~25 мин
### intro
**Слова шага:** *проверка устойчивости данных*, *`kubectl exec` в БД*.

:::tip Если совсем просто
Самое убедительное доказательство — не прочитать документацию, а своими руками убить Pod и своими глазами увидеть, что данные на месте. Доверяй, но проверяй — особенно в инфраструктуре, где ошибка стоит реальных данных.
:::

```bash run
kubectl exec deploy/db -- psql -U coffeeshop -d coffeeshop -c "CREATE TABLE IF NOT EXISTS t(id serial, note text); INSERT INTO t(note) VALUES ('переживу пересоздание');"
podname=$(kubectl get pods -l app=db -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod "$podname"
kubectl wait --for=condition=Available deployment/db --timeout=60s
kubectl exec deploy/db -- psql -U coffeeshop -d coffeeshop -c "SELECT * FROM t;"
```

### result
```out auto
```

Новый Pod (с новым именем, другим IP) поднимается, подключает **тот же** PVC, и строка, записанная в старом Pod, видна в новом — потому что данные жили не в Pod, а в PersistentVolume, который существует независимо от того, какой Pod к нему подключён сейчас.

### why
Это главный практический вывод всей сессии: PVC делает Pod **одноразовым и заменяемым** даже для stateful-сервисов — то самое self-healing из сессии 4, но теперь с сохранением данных.

### deep Если не получилось
- **Таблица пустая после пересоздания** — проверь `kubectl describe pod <новый>` → смонтирован ли тот же PVC (`claimName: db-data`), и что PVC не пересоздавался между шагами.

### quiz
- Почему данные сохранились, хотя сам Pod был удалён и пересоздан с другим именем и IP?
- Что именно — Pod или PVC — является «держателем» реальных данных?

### links
- https://kubernetes.io/docs/concepts/storage/persistent-volumes/#lifecycle-of-a-volume-and-claim | жизненный цикл PV и PVC | Kubernetes: Lifecycle of a Volume and Claim

## 6.5 StatefulSet: стабильные имена и тома | short: StatefulSet | est: ~35 мин
### intro
**Слова шага:** *StatefulSet*, *стабильное сетевое имя*, *`volumeClaimTemplates`*, *порядковый номер реплики*.

:::tip Если совсем просто
Deployment — это гостиница, где всем номерам всё равно, какой гость в каком живёт (главное — чтобы было N занятых). StatefulSet — это общежитие с **именными** комнатами: `db-0`, `db-1`, `db-2` — у каждой свой постоянный адрес и своя персональная кладовка (том), и даже если жилец комнаты `db-1` съедет и заедет новый — это всё равно будет именно `db-1` со своим именным томом, не общим с соседями.
:::

Для одной реплики PostgreSQL (как у нас) разница Deployment/StatefulSet не критична — но StatefulSet становится нужен, когда баз несколько и каждая должна иметь **свой собственный** том и предсказуемое имя (кластер PostgreSQL с репликацией, Kafka, Elasticsearch):

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: db
spec:
  serviceName: db-headless
  replicas: 1
  selector:
    matchLabels: {app: db}
  template:
    metadata:
      labels: {app: db}
    spec:
      containers:
        - name: postgres
          image: postgres:18
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: [ReadWriteOnce]
        resources:
          requests: {storage: 1Gi}
```

Ключевое отличие от Deployment: **`volumeClaimTemplates`** вместо ссылки на один готовый PVC — StatefulSet создаёт **отдельный** PVC для **каждой** реплики (`data-db-0`, `data-db-1`, …), и при пересоздании `db-1` подключается именно к `data-db-1`, никогда — к чужому тому. Имена Pod тоже предсказуемые (`db-0`, `db-1`, не случайный хэш, как у Deployment) и требуют `headless`-сервис (сессия 5.2), чтобы DNS-имя `db-1.db-headless` указывало именно на эту реплику.

### result
Применять на нашем одно-репличном PostgreSQL не будем — Deployment с одним PVC (как в шаге 6.3) достаточен и проще. Это шаг для понимания инструмента: StatefulSet появится практически в любой реальной задаче с БД, как только реплик становится больше одной.

### why
Частая ошибка на собеседованиях и в реальных задачах — пытаться масштабировать stateful-сервис через обычный Deployment с общим PVC: несколько Pod с `ReadWriteOnce`-томом одновременно работать не смогут (конфликт блокировок), а с `ReadWriteMany` — рискуют повредить данные, если сама СУБД не поддерживает параллельный доступ к файлам. StatefulSet решает это, давая каждой реплике **свой** том с первого дня.

### deep Если не получилось понять разницу с Deployment
Сравни имена: `kubectl get pods -l app=coffeeshop-api` даёт случайные хэши (Deployment), а гипотетический `kubectl get pods -l app=db` для StatefulSet дал бы `db-0`, `db-1` — по возрастанию, без хэшей. Порядок создания и удаления реплик у StatefulSet тоже строгий (по возрастанию номера при создании, по убыванию при удалении) — у Deployment порядка нет вовсе.

### quiz
- В чём разница между тем, как Deployment и StatefulSet выдают тома своим репликам?
- Почему обычный Deployment с одним общим PVC не подходит для нескольких реплик stateful-сервиса?
- Что отличает имена Pod у StatefulSet от имён у Deployment?

### links
- https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/ | StatefulSet | Kubernetes: StatefulSet
- https://kubernetes.io/docs/tasks/run-application/run-replicated-stateful-application/ | пример реплицированного stateful-приложения | Kubernetes: Run a Replicated Stateful Application

## 6.6 Резервная копия и обзор CronJob | short: pg_dump и CronJob | est: ~25 мин
### intro
**Слова шага:** *`pg_dump` через `kubectl exec`*, *CronJob (обзор)*.

:::tip Если совсем просто
`kubectl exec ... -- pg_dump` — это то же самое, что ты делала бы `docker exec` в Compose, просто через API Kubernetes. CronJob — будильник, который сам нажимает «выполнить задачу» по расписанию, не дожидаясь, что ты вспомнишь сделать это руками в пятницу вечером.
:::

```bash run
kubectl exec deploy/db -- pg_dump -U coffeeshop coffeeshop > /tmp/coffeeshop-backup.sql
wc -l /tmp/coffeeshop-backup.sql
```

### result
```out auto
```

Резервная копия оказалась **на твоём Mac** (не внутри кластера) — именно поэтому команда выглядит как `kubectl exec ... > файл`, а не просит `pg_dump` писать файл внутрь контейнера: внутри Pod файл исчез бы вместе с Pod, если не класть его явно в PVC.

**CronJob** (подробно — сессия 8.4, здесь только обзор) умеет делать это **по расписанию**, без твоего участия:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: db-backup
spec:
  schedule: "0 3 * * *"   # каждый день в 03:00
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: pg-dump
              image: postgres:18
              command: ["sh", "-c", "pg_dump -h db -U coffeeshop coffeeshop > /backup/dump-$(date +%F).sql"]
              volumeMounts:
                - {name: backup, mountPath: /backup}
          volumes:
            - name: backup
              persistentVolumeClaim: {claimName: backup-data}
```

### result
Применять не будем — применим и разберём механизм Job/CronJob подробно в сессии 8.4, где у нас уже будет вся нужная теория про шаблон Pod внутри Job. Здесь достаточно увидеть форму записи расписания (`cron`-синтаксис: минута, час, день месяца, месяц, день недели) и что результат должен сохраняться в **отдельный** PVC, а не теряться вместе с Pod задачи.

### why
Привычка «бэкап — это Job по расписанию, а не ручная команда, которую не забыть выполнить» — то, что отличает реальную эксплуатацию от учебного стенда. Резервные копии вне самого кластера (внешнее хранилище, не локальный PVC) — тема за пределами этой лабы, но важно знать, что PVC внутри того же `kind`-кластера — не защита от потери **всего** кластера.

### quiz
- Почему резервная копия в примере выше кладётся на отдельный PVC, а не просто в файловую систему контейнера задачи?
- Что означает расписание `"0 3 * * *"`?

### links
- https://www.postgresql.org/docs/current/app-pgdump.html | pg_dump | PostgreSQL: pg_dump
- https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/ | CronJob | Kubernetes: CronJob

## 6.7 🔨 PVC в Pending: StorageClass и accessMode | short: 🔨 PVC Pending | est: ~30 мин
### intro
**Слова шага:** *PVC навечно в `Pending`*, *несуществующий StorageClass*, *несовпадающий `accessMode`*.

:::tip Если совсем просто
Заявка на флешку с несуществующим артикулом склада («дай мне StorageClass, которого нет») будет лежать в ящике «в обработке» вечно — никто не придёт её выполнять, но и явной ошибки склад не выдаст: просто тишина. Твоя задача — заметить, что заявка висит ненормально долго, и посмотреть, что в ней не так.
:::

```bash run
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: broken-pvc
spec:
  storageClassName: does-not-exist
  accessModes: [ReadWriteOnce]
  resources:
    requests: {storage: 1Gi}
EOF
sleep 3
kubectl get pvc broken-pvc
kubectl describe pvc broken-pvc | tail -8
```

### result
```out auto
```

`kubectl get pvc` показывает статус **`Pending`**, и это — единственный внешний симптом: никакой ошибки в терминале при создании не было (манифест синтаксически валиден, просто ссылается на несуществующий StorageClass). `kubectl describe` в Events покажет что-то вроде `waiting for a volume to be created, either by external provisioner "does-not-exist" or manually created by system administrator`.

Второй типичный случай — StorageClass существует, но запрошенный `accessMode` не поддерживается конкретным провизионером (например, `ReadWriteMany` на провайдере, который умеет только `ReadWriteOnce`):

```bash run
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: broken-pvc-mode
spec:
  accessModes: [ReadWriteMany]
  resources:
    requests: {storage: 1Gi}
EOF
sleep 3
kubectl get pvc broken-pvc-mode
kubectl delete pvc broken-pvc broken-pvc-mode
```

### result
```out auto
```

### why
`Pending` без явной ошибки — особенно неприятный случай для новичка: нет «красного текста», который сразу бросается в глаза, как было с `ImagePullBackOff`. Привычка проверять `describe` **любого** объекта, который «висит», а не только явно ошибающегося, — общий урок, который пригодится и дальше (сессия 8.6).

### deep Если не получилось
- **`broken-pvc-mode` неожиданно перешёл в `Bound`** — значит, StorageClass по умолчанию в твоей версии `kind`/`local-path` на самом деле поддерживает запрошенный режим, или ты используешь другой провайдер (CSI); не все окружения ведут себя одинаково — ориентируйся на `describe`, а не только на итоговый статус.

### quiz
- Какой статус показывает `kubectl get pvc`, если `StorageClass` не существует, и чем он отличается от явной ошибки?
- Где искать причину, если PVC висит в `Pending` без красного текста при создании?

### links
- https://kubernetes.io/docs/concepts/storage/persistent-volumes/#class-1 | StorageClass у PVC | Kubernetes: Class
- https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes | режимы доступа | Kubernetes: Access Modes

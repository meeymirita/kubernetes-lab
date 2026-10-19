# Сессия 5 · Сети и Ingress
dur: ~4 ч

## 5.1 Сетевая модель: у каждого Pod свой IP | short: Сетевая модель | est: ~30 мин
### intro
**Слова шага:** *CNI*, *flat network*, *Pod-to-Pod без NAT*.

:::tip Если совсем просто
В Docker Compose все контейнеры одного проекта сидят в своей отдельной сети, и чтобы попасть из одного проекта в другой, нужны мосты и публикация портов. В Kubernetes все Pod во **всём кластере** — как квартиры в одном огромном доме без домофонов между этажами: любой Pod может напрямую достучаться по IP до любого другого, на любом узле, без перевода адресов (NAT) и без явного «подружи эти две сети».
:::

Фундаментальное правило сети Kubernetes (его обязан реализовать **CNI** — сетевой плагин, в `kind` это `kindnet` по умолчанию, шаг 9.5 заменит его на Calico для одной задачи):

- У каждого Pod — **свой собственный IP**, уникальный в рамках кластера.
- Любой Pod может обратиться к любому другому Pod **по этому IP напрямую**, даже если они на разных узлах — без NAT, без ручной настройки маршрутов.
- Узел (сам по себе) тоже может достучаться до любого Pod на себе и на других узлах.

```bash run
kubectl get pods -l app=coffeeshop-api -o wide
pod_ip=$(kubectl get pods -l app=coffeeshop-api -o jsonpath='{.items[0].status.podIP}')
kubectl run net-test --image=busybox:1.36 --rm -it --restart=Never -- wget -qO- "http://$pod_ip:3000/health"
```

### result
```out auto
```

Тестовый Pod достучался до API **по его сырому IP**, даже не зная, что это именно CoffeeShop API — так работает сеть на самом базовом уровне, до появления Service.

### why
Это объясняет, почему Service (сессия 3.4) — это слой **удобства**, а не единственный способ связи: сеть между Pod работает и без него. Но без Service ты бы постоянно отслеживала меняющиеся IP вручную — поэтому в манифестах мы всегда обращаемся через Service, а не через прямой IP Pod.

### deep CNI — это не один инструмент
«Container Network Interface» — это **спецификация**, по которой сетевые плагины подключаются к Kubernetes; реализаций много: `kindnet` (встроенный в `kind`, простой, без поддержки `NetworkPolicy`), Calico, Cilium, Flannel — у каждой свои возможности (сессия 9.5 разберёт это на практике с `NetworkPolicy`).

### deep Если не получилось
- **`wget` не отвечает** — проверь, что IP взят из **живого** Pod (`kubectl get pods` — если Pod пересоздался между командами, IP изменился, сессия 2.2).

### quiz
- Какое фундаментальное правило должен обеспечивать любой CNI-плагин?
- Почему прямой доступ по IP Pod работает, но в манифестах мы всё равно используем Service?
- Что такое CNI — конкретная программа или спецификация?

### links
- https://kubernetes.io/docs/concepts/cluster-administration/networking/ | сетевая модель Kubernetes | Kubernetes: Cluster Networking
- https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/ | сетевые плагины (CNI) | Kubernetes: Network Plugins

## 5.2 Типы Service: ClusterIP, NodePort, LoadBalancer | short: Типы Service | est: ~35 мин
### intro
**Слова шага:** *`ClusterIP`*, *`NodePort`*, *`LoadBalancer`*, *`headless`-сервис*.

:::tip Если совсем просто
`ClusterIP` — внутренний городской телефон (звонить можно только из того же здания). `NodePort` — тот же телефон, но с добавочным номером, который можно набрать снаружи здания, зная номер любого этажа (узла). `LoadBalancer` — отдельная линия с автоответчиком у входа, которую заказывает и оплачивает телефонная компания (облачный провайдер) — в `kind` своего провайдера нет, поэтому за эту роль у нас отвечает Traefik через Ingress (следующие шаги).
:::

| Тип | Доступен | Как |
|---|---|---|
| `ClusterIP` (по умолчанию) | только внутри кластера | виртуальный IP, DNS-имя |
| `NodePort` | снаружи, через **любой** узел | фиксированный порт (30000–32767) на каждом узле |
| `LoadBalancer` | снаружи, через внешний балансировщик | в `kind` — не работает «из коробки» (нет облачного API, который бы его создал); эмулируется `MetalLB` или просто остаётся `<pending>` |
| `headless` (`clusterIP: None`) | внутри кластера, но без единого виртуального IP | DNS отдаёт **все** IP Pod по очереди — используется StatefulSet (сессия 6.5) |

```bash run
kubectl expose deployment coffeeshop-api --name=coffeeshop-api-nodeport --type=NodePort --port=80 --target-port=3000
kubectl get svc coffeeshop-api-nodeport
```

### result
```out auto
```

Увидим что-то вроде `80:31500/TCP` — порт `31500` (случайный из диапазона, если не указать явно) открыт **на каждом узле кластера**; на реальном железе это означало бы «подключись к IP любой машины кластера на этом порту». У `kind` узлы — Docker-контейнеры, так что доступ с Mac всё равно требует либо `extraPortMappings` (как мы сделали для control-plane в шаге 1.5), либо `kubectl port-forward`.

Убираем лишний Service — в лабе мы будем открывать CoffeeShop только через Ingress:

```bash run
kubectl delete svc coffeeshop-api-nodeport
```

### why
`NodePort` — учебная ступенька и способ отладки, но для реального продакшн-доступа почти всегда используют `LoadBalancer` (в облаке) или, как у нас, Ingress поверх `ClusterIP` — именно этим мы займёмся дальше. `headless`-сервисы — отдельный инструмент для случаев, когда нужен доступ к **каждой конкретной** реплике (StatefulSet, сессия 6.5), а не к случайной через балансировку.

### deep Если не получилось
- **`<pending>` у `type: LoadBalancer`** — ожидаемо в `kind` без `MetalLB`: никто не выдаёт внешний IP; это не ошибка, а честное отсутствие облачного провайдера.

### quiz
- Чем `NodePort` отличается от `ClusterIP` по доступности?
- Почему `type: LoadBalancer` висит в `<pending>` в кластере `kind`?
- Для какого паттерна нужен `headless`-сервис?

### links
- https://kubernetes.io/docs/concepts/services-networking/service/#publishing-services-service-types | типы Service | Kubernetes: Publishing Services
- https://kubernetes.io/docs/concepts/services-networking/service/#headless-services | headless Service | Kubernetes: Headless Services

## 5.3 DNS кластера: как резолвится имя | short: DNS кластера | est: ~25 мин
### intro
**Слова шага:** *CoreDNS*, *`resolv.conf` Pod*, *цепочка поиска доменов*.

:::tip Если совсем просто
Каждый Pod получает «записную книжку» с короткими номерами: набрал `db` — а телефон сам понимает, что это `db.default.svc.cluster.local`, потому что настроен искать именно в этом «районе» первым делом. Это и есть `resolv.conf` внутри Pod, которую настраивает CoreDNS.
:::

```bash run
kubectl run dns-check --image=busybox:1.36 --rm -it --restart=Never -- sh -c "cat /etc/resolv.conf && nslookup coffeeshop-api"
```

### result
```out auto
```

`/etc/resolv.conf` внутри Pod указывает на **IP CoreDNS** (Service `kube-dns` в `kube-system`) как единственный DNS-сервер и содержит `search`-список доменов (`default.svc.cluster.local`, `svc.cluster.local`, `cluster.local` — по порядку), благодаря которому короткое имя `coffeeshop-api` без лишних частей резолвится в правильный Service.

### why
Если DNS внутри кластера вдруг не работает (`nslookup` не находит сервисы, которые точно есть), это почти всегда симптом поломки самого CoreDNS (посмотри `kubectl get pods -n kube-system -l k8s-app=kube-dns`), а не проблема конкретного приложения — стоит проверить это **до** того, как начинать разбирать логи самого приложения.

### deep Если не получилось
- **`nslookup`: `can't resolve`** — проверь, что Service существует в том же namespace, что тестовый Pod; из другого namespace нужно хотя бы `coffeeshop-api.default`.

### quiz
- Куда указывает `/etc/resolv.conf` внутри Pod и кто его настраивает?
- Что произойдёт, если CoreDNS в `kube-system` не здоров?

### links
- https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/ | DNS Pod и Service | Kubernetes: DNS for Services and Pods

## 5.4 Зачем Ingress: Traefik в кластере | short: Ingress Controller | est: ~45 мин
### intro
**Слова шага:** *Ingress*, *Ingress Controller*, *`IngressClass`*, *HTTP-уровень вместо TCP-уровня*.

:::tip Если совсем просто
`NodePort`/`LoadBalancer` открывают дверь **для одного конкретного сервиса на отдельном порту** — это как дать каждому сотруднику кофейни отдельный личный вход с улицы. Ingress — один общий ресепшн на весь бизнес-центр: посетитель называет, к кому пришёл (`Host`, путь), и ресепшн (Ingress Controller — реальная программа, которая слушает 80/443) сам отводит его в нужный кабинет (Service). Это ровно та же роль, что у Traefik в прошлой лабе — просто теперь прописанная языком Kubernetes.
:::

```svg
@ingress-reception
```

**Ingress** (ресурс, `apiVersion: networking.k8s.io/v1`) — это только **правила**: «если `Host` такой и путь такой — веди на вот этот Service». Сам ресурс **ничего не слушает** и трафик не обрабатывает — для этого нужен **Ingress Controller**: реальная программа (у нас — Traefik v3.7), которая читает Ingress-ресурсы из API и настраивает себя по ним. Без установленного контроллера Ingress-ресурс — просто текст, который никто не выполняет (в отличие от `Service`/`Deployment`, у которых исполнители — встроенные контроллеры control plane).

Напомним, почему именно Traefik, а не `ingress-nginx`: проект `ingress-nginx` **официально свёрнут** SIG Network в ноябре 2025 года (лучшие усилия по поддержке — до марта 2026, после — репозиторий заморожен без новых релизов и патчей безопасности); Traefik активно развивается и — приятный бонус для тебя — ты уже знаешь его модель «роутер → middleware → сервис» из Traefik-лабы.

Установим Traefik через Helm (забегая немного вперёд — сам Helm подробно в сессии 12, здесь используем его как самый быстрый путь к рабочему Ingress Controller):

```bash run
helm repo add traefik https://traefik.github.io/charts
helm repo update
helm install traefik traefik/traefik \
  --namespace traefik --create-namespace \
  --set ports.web.hostPort=80 --set ports.websecure.hostPort=443 \
  --set hostNetwork=true --set service.type=ClusterIP
kubectl get pods -n traefik
kubectl get ingressclass
```

### result
```out auto
```

`kubectl get ingressclass` покажет `traefik` — это то имя, на которое Ingress-ресурсы будут ссылаться (`spec.ingressClassName: traefik`), если в кластере несколько Ingress Controller и нужно явно выбрать, какой из них должен обслуживать конкретный ресурс (у нас он один — но поле лучше указывать явно с первого дня, по аналогии с `traefik.enable` в прошлой лабе).

### why
Ingress Controller — это концептуально тот же Traefik, что ты ставила в Docker Compose, просто источник конфигурации сменился с меток контейнеров на ресурсы Kubernetes API (`Ingress`, а для более богатых возможностей — `IngressRoute`, следующий шаг). Сама модель «роутер → middleware → сервис» не изменилась ни на бит.

### deep Почему не `api.insecure`/метки, как раньше
В Kubernetes у Traefik нет Docker-провайдера (нет `docker.sock` — мы вообще не в Docker Compose) — вместо него Traefik использует **Kubernetes-провайдер**: он слушает API-сервер через `kubectl`-подобный доступ (с правами через RBAC, сессия 9.1) и строит маршруты из `Ingress`/`IngressRoute`.

### deep Если не получилось
- **Pod Traefik не стартует (`CrashLoopBackOff`)** — чаще всего конфликт порта 80/443 на узле (`hostNetwork: true` требует, чтобы порт был свободен именно на том узле, где запланирован Pod); проверь, не занят ли порт другим процессом.

### quiz
- Что делает Ingress-ресурс сам по себе, без установленного Ingress Controller?
- Почему лаба выбрала Traefik, а не `ingress-nginx`?
- Для чего нужно поле `ingressClassName`?

### links
- https://kubernetes.io/docs/concepts/services-networking/ingress/ | Ingress | Kubernetes: Ingress
- https://kubernetes.io/blog/2025/11/11/ingress-Nginx-retirement/ | решение о сворачивании ingress-nginx | Kubernetes Blog: Ingress NGINX Retirement
- https://doc.traefik.io/traefik/providers/kubernetes-ingress/ | провайдер Kubernetes Ingress у Traefik | Traefik: Kubernetes Ingress Provider

## 5.5 Ingress и IngressRoute: маршрутизация по Host и пути | short: Ingress и IngressRoute | est: ~45 мин
### intro
**Слова шага:** *`Ingress`*, *`IngressRoute` (CRD Traefik)*, *`pathType`*, *CRD*.

:::tip Если совсем просто
`Ingress` — это заявление по стандартной государственной форме, которую понимает **любой** Ingress Controller (переносимо между Traefik, `ingress-nginx` и облачными решениями, но с ограниченным набором полей). `IngressRoute` — это собственный, более подробный бланк именно Traefik (CRD — «Custom Resource Definition», способ Kubernetes дать стороннему продукту свой тип объекта) — со всеми теми же возможностями из прошлой лабы: `Host()`, `PathPrefix()`, приоритеты, пока без middleware (они — сессия 7.6 для заголовков).
:::

Сначала — переносимый, стандартный `Ingress`:

```bash run
cat > manifests/04-ingress.yaml <<'EOF'
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: coffeeshop
  annotations:
    kubernetes.io/ingress.class: traefik
spec:
  ingressClassName: traefik
  rules:
    - host: shop.localhost
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: coffeeshop-api
                port:
                  number: 80
          - path: /
            pathType: Prefix
            backend:
              service:
                name: coffeeshop-web
                port:
                  number: 80
EOF
kubectl apply -f manifests/04-ingress.yaml
kubectl get ingress coffeeshop
```

### result
```out auto
```

`pathType: Prefix` — совпадает с запросом, если его путь **начинается** с указанного (`/api/menu` подходит под `/api`); альтернатива `Exact` — только буквально такой же путь. Правила в списке `rules[].http.paths` проверяются в порядке **длины совпадения пути** внутри одного `Host` — поэтому `/api` в примере сработает для запросов на `/api/...`, а всё остальное попадёт на `/` (web).

Чтобы получить ровно то же, что давали метки Traefik в прошлой лабе (включая middleware позже), используем **`IngressRoute`** — собственный CRD Traefik:

```bash run
kubectl apply -f - <<'EOF'
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: coffeeshop-web
spec:
  entryPoints: [web]
  routes:
    - match: Host(`shop.localhost`) && PathPrefix(`/`)
      kind: Rule
      services:
        - name: coffeeshop-web
          port: 80
EOF
kubectl get ingressroute
```

### result
```out auto
```

Правило `Host(...) && PathPrefix(...)` — буквально тот же синтаксис, что в метках Traefik Docker-провайдера (Traefik-лаба, сессия 3) — только теперь это манифест Kubernetes, а не строка метки.

### why
Стандартный `Ingress` — минимальный общий знаменатель (переносим между контроллерами), `IngressRoute` — полный набор возможностей конкретно Traefik (middleware, TCP/UDP-роутеры, веса для canary — сессия 12). В реальных проектах часто используют именно `IngressRoute`/аналоги других контроллеров ради возможностей, принимая привязку к конкретному Ingress Controller как осознанную цену.

### deep Как узнать Kubernetes о новом типе CRD
`IngressRoute` существует только потому, что Helm chart Traefik при установке (шаг 5.4) создал **CustomResourceDefinition** — манифест, который говорит API-серверу «теперь ты понимаешь ещё и такой тип объекта». `kubectl get crd | grep traefik` покажет все добавленные Traefik типы.

### deep Если не получилось
- **`no matches for kind "IngressRoute"`** — CRD не установился; проверь `kubectl get crd` и, при необходимости, переустанови chart Traefik (`helm upgrade`, сессия 12).

### quiz
- Чем `Ingress` отличается от `IngressRoute` по переносимости между контроллерами?
- Что такое CRD и откуда Kubernetes «узнал» про `IngressRoute`?
- Как Traefik выбирает, какое из нескольких правил `paths` применить к конкретному запросу?

### links
- https://kubernetes.io/docs/concepts/services-networking/ingress/#the-ingress-resource | ресурс Ingress подробно | Kubernetes: The Ingress Resource
- https://doc.traefik.io/traefik/routing/providers/kubernetes-crd/ | IngressRoute (CRD) | Traefik: Kubernetes CRD

## 5.6 kind и порты: открываем с Mac | short: Порты kind | est: ~25 мин
### intro
**Слова шага:** *`extraPortMappings`*, *`/etc/hosts`*, *`*.localhost`*.

:::tip Если совсем просто
Мы уже проложили «трубу» с портов 80/443 твоего Mac прямо в control-plane-узел кластера ещё в шаге 1.5 — пришло время ею воспользоваться. Домен `shop.localhost` особенный: современные браузеры и `curl` сами резолвят **любое** имя, заканчивающееся на `.localhost`, в `127.0.0.1` — без правки `/etc/hosts`, в отличие от придуманных доменов вида `.test`.
:::

```bash run
curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://shop.localhost/
curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://shop.localhost/api/health
```

### result
```out auto
```

Путь запроса целиком: твой Mac (`http://shop.localhost/`) → порт 80 → `extraPortMappings` → control-plane-узел `kind` → Pod Traefik (слушает на этом узле благодаря `hostNetwork: true`) → Traefik смотрит `IngressRoute`/`Ingress` → находит Service `coffeeshop-web`/`coffeeshop-api` → Service находит живой Pod по `selector` → ответ.

### why
Это — ровно тот результат, к которому шла вся Traefik-лаба: единый вход с человекочитаемыми именами вместо портов. В Kubernetes он достигается тем же способом (reverse proxy на входе), просто конфигурация Traefik теперь берётся не из меток Docker, а из API кластера.

### deep Если порт 80 занят на Mac
Поменяй `hostPort` в `kind-config.yaml` (шаг 1.5) на свободный, например `8000`, и пересоздай кластер — тогда адреса читаются как `http://shop.localhost:8000/`.

### deep Если не получилось
- **`curl: (7) Failed to connect`** — проверь по порядку: узел control-plane жив (`docker ps`) → Pod Traefik `Running` (`kubectl get pods -n traefik`) → `extraPortMappings` в `kind-config.yaml` совпадают с тем, что реально слушает Traefik.

### quiz
- Почему `*.localhost` работает без правки `/etc/hosts`, а произвольный домен вида `shop.test` — не работает?
- Опиши весь путь запроса от браузера на Mac до Pod с приложением.

### links
- https://kind.sigs.k8s.io/docs/user/ingress/ | Ingress в kind | kind: Ingress

## 5.7 🔨 Ingress есть, а 404/503 | short: 🔨 Ingress есть, а 404 | est: ~35 мин
### intro
**Слова шага:** *диагностика Ingress*, *Service без endpoints*, *несовпадение правила*.

:::tip Если совсем просто
Это тот же диагностический танец, что был в Traefik-лабе про «роутер есть, а 404»: только теперь вместо дашборда Traefik — `kubectl describe ingress` и проверка Service/endpoints по отдельности от самого Ingress.
:::

Сломаем Ingress на новый сервис с опечаткой в имени Service:

```bash run
kubectl apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: coffeeshop-broken
spec:
  ingressClassName: traefik
  rules:
    - host: broken.shop.localhost
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: coffeeshop-apiii
                port:
                  number: 80
EOF
curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://broken.shop.localhost/
kubectl describe ingress coffeeshop-broken | tail -8
```

### result
```out auto
```

`describe` покажет событие вроде `Service "coffeeshop-apiii" not found` или Traefik отдаст `503`/`404` в зависимости от версии и настроек — **первое**, что нужно проверить, — существует ли Service с именем **буквально таким**, как в Ingress.

Второй типичный случай — Service есть, но у него нет живых Pod (как в сессии 3.4):

```bash run
kubectl scale deployment coffeeshop-api --replicas=0
sleep 3
curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://shop.localhost/api/health
kubectl get endpoints coffeeshop-api
kubectl scale deployment coffeeshop-api --replicas=3
kubectl delete ingress coffeeshop-broken
```

### result
```out auto
```

При нулевых репликах `endpoints` пуст — Traefik честно отвечает `503 Service Unavailable` («сервис существует, но ответить некому»), а не `404` (который означал бы «не нашла правило»).

### why
Таблица из диагностики Traefik-лабы работает и здесь почти буквально: **404** — проблема правила/Ingress (нет маршрута, опечатка в `Host`/`host`), **503** — Service есть, но `endpoints` пуст (нет живых Pod под selector), **502** — Pod есть, но порт неверный или приложение не отвечает. Три вопроса по порядку: Ingress нашёл правило? Service нашёл Pod? Pod отвечает сам?

### deep Если не получилось
- **Долго не появляется `404`/`503`, висит `Timeout`** — Traefik не может **достучаться** до узла или Service: проверь `kubectl get pods -n traefik` и сеть (сессия 5.1).

### quiz
- О чём говорит `404` от Traefik в Kubernetes в отличие от `503`?
- Какую команду проверяешь первой, когда Ingress создан, а ответ — ошибка?
- Как отличить «Service не нашёл Pod» от «Pod не отвечает на запросы»?

### links
- https://kubernetes.io/docs/concepts/services-networking/ingress/#debugging-ingress | диагностика Ingress | Kubernetes: Debugging Ingress
- https://doc.traefik.io/traefik/operations/dashboard/ | дашборд Traefik (тоже доступен в Kubernetes) | Traefik: Dashboard

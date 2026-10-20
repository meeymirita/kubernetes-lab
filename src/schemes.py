# -*- coding: utf-8 -*-
"""Схемы Kubernetes Lab: python3 kubernetes/src/schemes.py [имя] -> kubernetes/src/schemes/<имя>.html (вставляются в методичку блоком ```svg @имя)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../fixes/common/_tools'))
from svgkit import Svg  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schemes')
S = {}


def scheme(f):
    S[f.__name__.replace('_', '-')] = f
    return f


@scheme
def cluster_anatomy():
    s = Svg(700, 300, 'Кластер kind: узел control-plane с API-сервером и два рабочих узла; kubectl разговаривает только с API-сервером', pid='ca')
    s.box(10, 110, 100, 56, ['kubectl', 'на твоём Mac'], fill=.1, bold=True, size=11)
    s.box(170, 20, 520, 120, [], fill=.04, dash=True)
    s.text(430, 40, 'control-plane  (контейнер coffeeshop-control-plane)', size=12, weight='700')
    s.box(185, 58, 120, 66, ['API-сервер', 'единственная', '«дверь»'], fill=.2, bold=True, size=11)
    s.box(320, 58, 90, 66, ['etcd', 'память'], fill=.12, size=11)
    s.box(425, 58, 110, 66, ['scheduler', 'выбирает узел'], fill=.12, size=11)
    s.box(550, 58, 125, 66, ['контроллеры', 'следят за', 'порядком'], fill=.12, size=11)
    s.arrow(110, 138, 183, 100, 'команды', ly=108)
    for i, name in enumerate(['worker', 'worker2']):
        x = 170 + i * 270
        s.box(x, 180, 250, 100, [], fill=.04, dash=True)
        s.text(x + 125, 200, 'узел ' + name, size=12, weight='700')
        s.box(x + 12, 212, 100, 56, ['kubelet', 'агент узла'], fill=.14, size=11)
        s.box(x + 125, 212, 112, 56, ['Pod  Pod', 'контейнеры'], fill=.08, size=11)
    s.arrow(245, 124, 245, 178, dash=True)
    s.arrow(515, 124, 400, 178, dash=True)
    s.text(100, 250, 'аналогия: секретарь принимает', size=11, op=.85)
    s.text(100, 266, 'все просьбы, исполнители', size=11, op=.85)
    s.text(100, 282, 'работают на местах', size=11, op=.85)
    return s.html()


@scheme
def apply_path():
    s = Svg(700, 230, 'Путь kubectl apply: API-сервер, etcd, контроллер, scheduler, kubelet', pid='ap')
    steps = [('kubectl', 'apply -f'), ('API-сервер', 'проверка, запись'), ('etcd', 'желаемое'), ('контроллер', 'создаёт Pod'), ('scheduler', 'выбирает узел'), ('kubelet', 'запускает')]
    w, g = 96, 20
    for i, (a, b) in enumerate(steps):
        x = 6 + i * (w + g)
        s.box(x, 70, w, 62, [a, b], fill=.08 + i * .03, bold=True, size=11)
        if i < len(steps) - 1:
            s.arrow(x + w, 101, x + w + g, 101)
    s.text(350, 28, 'письмо → сортировка → доставка → подтверждение', size=13, weight='700')
    s.text(350, 170, 'каждый компонент делает свою часть и записывает результат обратно в API-сервер', size=11, op=.85)
    s.text(350, 196, 'если Pod не появился — смотри, на каком шаге цепочка оборвалась (describe → Events)', size=11, op=.85)
    return s.html()


@scheme
def service_stable_address():
    s = Svg(700, 250, 'Service даёт один стабильный адрес на несколько Pod, чьи адреса меняются', pid='ss')
    s.box(10, 100, 90, 50, ['Клиент'], fill=.1, bold=True)
    s.box(170, 90, 150, 70, ['Service  db', 'ClusterIP 10.96.x.x', 'стойка регистрации'], fill=.22, bold=True, size=11)
    s.arrow(100, 125, 168, 125)
    for i, (n, ip) in enumerate([('Pod  api-1', '10.244.1.5'), ('Pod  api-2', '10.244.2.7'), ('Pod  api-3', '10.244.1.9')]):
        y = 30 + i * 70
        s.box(420, y, 130, 52, [n, ip], fill=.08, size=11, dash=(i == 2))
        s.arrow(320, 125, 418, y + 26)
    s.text(620, 70, 'номера (Pod)', size=12, weight='700')
    s.text(620, 88, 'меняются, умирают,', size=11, op=.85)
    s.text(620, 104, 'рождаются заново', size=11, op=.85)
    s.text(620, 160, 'стойка (Service)', size=12, weight='700')
    s.text(620, 178, 'всегда одна', size=11, op=.85)
    s.text(350, 236, 'Service находит Pod по меткам (selector) и берёт только готовых (readiness)', size=11, op=.85)
    return s.html()


@scheme
def rolling_update_wave():
    s = Svg(700, 260, 'Rolling update: новые Pod поднимаются волной, старые уходят по одному, сервис не останавливается', pid='ru')
    stages = [('старт', ['v1', 'v1', 'v1'], ''), ('+1 новый', ['v1', 'v1', 'v1', 'v2'], 'maxSurge'), ('−1 старый', ['v1', 'v1', 'v2', 'v2'], 'maxUnavailable'), ('финиш', ['v2', 'v2', 'v2'], '')]
    for r, (t, pods, note) in enumerate(stages):
        y = 20 + r * 58
        s.text(70, y + 28, t, size=12, weight='700')
        for i, p in enumerate(pods):
            s.box(150 + i * 80, y + 6, 66, 38, [p], fill=.28 if p == 'v2' else .06, bold=True, size=12)
        if note:
            s.text(560, y + 30, note, size=11, op=.85)
    s.text(350, 252, 'конвейер: лента не останавливается, детали меняются по одной', size=11, op=.85)
    return s.html()


@scheme
def ingress_reception():
    s = Svg(700, 270, 'Путь запроса: браузер, Ingress Controller (Traefik), Service, Pod', pid='ir')
    s.box(10, 100, 90, 50, ['Браузер'], fill=.1, bold=True)
    s.box(150, 80, 150, 90, ['Traefik', 'Ingress Controller', ':80  :443', '«ресепшн»'], fill=.22, bold=True, size=11)
    s.arrow(100, 125, 148, 125, 'shop.localhost', ly=114)
    items = [('shop.localhost  /', 'Service web', 'Pod web'), ('shop.localhost  /api', 'Service api', 'Pod api'), ('adminer.shop.localhost', 'Service adminer', 'Pod adminer')]
    for i, (rule, svc, pod) in enumerate(items):
        y = 20 + i * 80
        s.box(350, y, 150, 50, [svc, rule], fill=.1, size=10)
        s.box(560, y, 120, 50, [pod], fill=.06, size=11)
        s.arrow(300, 125, 348, y + 25)
        s.arrow(500, y + 25, 558, y + 25)
    s.text(350, 262, 'Ingress — только правила; выполняет их контроллер (Traefik)', size=11, op=.85)
    return s.html()


@scheme
def pvc_survives_pod():
    s = Svg(700, 240, 'Том остаётся, когда Pod умирает: Pod, PVC, PV, диск', pid='pv')
    s.box(10, 70, 110, 60, ['Pod  db', 'ноутбук'], fill=.08, bold=True, size=11, dash=True)
    s.box(160, 70, 110, 60, ['PVC  db-data', 'заявка'], fill=.14, size=11)
    s.box(310, 70, 110, 60, ['PV', 'кусок хранилища'], fill=.14, size=11)
    s.box(460, 70, 110, 60, ['Диск', 'на узле'], fill=.22, bold=True, size=11)
    for x in (120, 270, 420):
        s.arrow(x, 100, x + 40, 100)
    s.box(590, 70, 100, 60, ['Pod  db (новый)'], fill=.08, bold=True, size=11)
    s.arrow(590, 100, 272, 100, dash=True)
    s.text(350, 40, 'флешка: ноутбук (Pod) можно заменить, файлы на флешке (диск) остаются', size=12, weight='700')
    s.text(350, 170, 'Pod удалён → PVC и PV остались → новый Pod подключает тот же PVC → данные на месте', size=11, op=.85)
    s.text(350, 196, 'данные пропадут только при удалении PVC (а при политике Delete — вместе с PV)', size=11, op=.85)
    return s.html()


@scheme
def config_secret_delivery():
    s = Svg(700, 250, 'ConfigMap и Secret подключаются к Pod как переменные окружения или файлы, отдельно от образа', pid='cs')
    s.box(10, 30, 150, 60, ['ConfigMap', 'api-config', 'LOG_LEVEL=info'], fill=.1, size=11)
    s.box(10, 140, 150, 60, ['Secret', 'db-credentials', 'POSTGRES_PASSWORD'], fill=.2, size=11)
    s.box(300, 70, 220, 110, [], fill=.04, dash=True)
    s.text(410, 92, 'Pod', size=13, weight='700')
    s.box(320, 104, 180, 60, ['контейнер api', 'образ coffeeshop-api:v1'], fill=.12, size=11)
    s.arrow(160, 60, 318, 120, 'envFrom / env', lx=230, ly=82)
    s.arrow(160, 170, 318, 150, 'secretKeyRef', lx=225, ly=170)
    s.box(560, 100, 130, 56, ['одно и то же', 'образ в dev и prod'], fill=.06, size=11)
    s.arrow(500, 134, 558, 128, dash=True)
    s.text(350, 236, 'рецепт (ConfigMap) и сейф с паролем (Secret) кладутся повару отдельно от блюда (образа)', size=11, op=.85)
    return s.html()


@scheme
def diagnosis_tree():
    s = Svg(700, 300, 'Дерево диагностики: статус Pod ведёт к вероятной причине', pid='dt')
    s.box(250, 8, 200, 40, ['kubectl get pods', 'какой STATUS?'], fill=.2, bold=True, size=11)
    rows = [('Pending', 'нет места / PVC / taint', 'describe → Events'), ('ImagePullBackOff', 'образ или тег', 'kind load, имя'), ('CrashLoopBackOff', 'падает при старте', 'logs --previous'), ('CreateContainerConfigError', 'нет ключа Secret', 'describe, имена'), ('Running 0/1', 'не проходит readiness', 'путь и порт пробы'), ('Running 1/1, а 503', 'Service / Ingress', 'endpoints, ingress')]
    for i, (st, why, act) in enumerate(rows):
        y = 70 + i * 38
        s.box(10, y, 190, 30, [st], fill=.12, bold=True, size=11)
        s.box(230, y, 220, 30, [why], fill=.06, size=11)
        s.box(480, y, 200, 30, [act], fill=.1, size=11)
        s.arrow(200, y + 15, 228, y + 15)
        s.arrow(450, y + 15, 478, y + 15)
    s.text(105, 62, 'симптом', size=11, op=.85)
    s.text(340, 62, 'вероятная причина', size=11, op=.85)
    s.text(580, 62, 'куда смотреть', size=11, op=.85)
    s.arrow(350, 48, 105, 66, dash=True)
    return s.html()


@scheme
def rbac_badge():
    s = Svg(700, 230, 'RBAC: кто (субъект), через RoleBinding, получает права Role на ресурсы', pid='rb')
    s.box(10, 80, 130, 60, ['jane', 'ServiceAccount', '(субъект)'], fill=.1, bold=True, size=11)
    s.box(210, 80, 140, 60, ['RoleBinding', 'выдача бейджа'], fill=.2, bold=True, size=11)
    s.box(420, 80, 120, 60, ['Role', 'pod-reader'], fill=.14, bold=True, size=11)
    s.box(590, 40, 100, 40, ['pods: get,', 'list, watch'], fill=.06, size=10)
    s.box(590, 100, 100, 40, ['secrets: —'], fill=.06, dash=True, size=10)
    s.box(590, 160, 100, 40, ['delete: —'], fill=.06, dash=True, size=10)
    s.arrow(140, 110, 208, 110)
    s.arrow(350, 110, 418, 110)
    s.arrow(540, 100, 588, 62)
    s.arrow(540, 110, 588, 120, dash=True)
    s.arrow(540, 120, 588, 178, dash=True)
    s.text(350, 20, 'пропускная система: бейдж открывает одни двери и не открывает другие', size=12, weight='700')
    s.text(350, 214, 'без RoleBinding у Role нет ни одного владельца; без Role бейдж открывает пустоту', size=11, op=.85)
    return s.html()


@scheme
def netpol_doors():
    s = Svg(700, 250, 'NetworkPolicy: к базе проходит только API, frontend заблокирован', pid='np')
    s.box(10, 30, 120, 50, ['Pod  web', 'app=web'], fill=.08, size=11)
    s.box(10, 150, 120, 50, ['Pod  api', 'app=api'], fill=.14, bold=True, size=11)
    s.box(330, 80, 150, 80, ['Pod  db', 'app=db', 'NetworkPolicy:', 'пускать app=api'], fill=.2, bold=True, size=11)
    s.arrow(130, 55, 328, 105, dash=True)
    s.text(215, 66, '✕ заперто', size=12, weight='700')
    s.arrow(130, 175, 328, 135)
    s.text(215, 172, '✓ порт 5432', size=12, weight='700')
    s.box(540, 80, 150, 80, ['CNI применяет', 'правила; без него', 'объект — просто', 'текст'], fill=.06, dash=True, size=10)
    s.arrow(538, 120, 482, 120, dash=True)
    s.text(350, 236, 'внутренние двери в офисе: сначала запираем всё, потом выдаём ключи нужным', size=11, op=.85)
    return s.html()


@scheme
def hpa_thermostat():
    s = Svg(700, 260, 'HPA как термостат: нагрузка растёт, число реплик растёт следом; потом возвращается', pid='hp')
    s.line(60, 30, 60, 200)
    s.line(60, 200, 660, 200)
    s.text(40, 34, 'нагр.', size=10, op=.8, anchor='end')
    s.text(36, 120, 'реплик', size=10, op=.8, anchor='end')
    s.path('M60,180 L180,180 L240,70 L400,70 L470,170 L660,180', arrow=False)
    s.path('M60,195 L200,195 L260,150 L330,100 L420,100 L540,150 L660,195', dash=True, arrow=False)
    s.text(300, 62, 'нагрузка (CPU)', size=11)
    s.text(380, 126, 'реплики', size=11)
    s.box(80, 215, 120, 30, ['minReplicas 2'], fill=.06, size=10)
    s.box(230, 215, 120, 30, ['рост быстрый'], fill=.06, size=10)
    s.box(380, 215, 120, 30, ['спад медленный'], fill=.06, size=10)
    s.box(530, 215, 120, 30, ['maxReplicas 6'], fill=.06, size=10)
    s.text(350, 18, 'жарче — включается больше кондиционеров, остыло — не сразу выключаются', size=11, op=.9)
    return s.html()


@scheme
def metrics_flow():
    s = Svg(700, 250, 'Поток метрик: Pod и узлы, Prometheus, Grafana; метрики забирает Prometheus сам', pid='mf')
    s.box(10, 30, 140, 60, ['Pod  api', 'kubelet / cAdvisor'], fill=.08, size=11)
    s.box(10, 110, 140, 60, ['kube-state-metrics', 'состояние объектов'], fill=.08, size=10)
    s.box(10, 190, 140, 50, ['Traefik  /metrics'], fill=.08, size=11)
    s.box(250, 80, 150, 80, ['Prometheus', 'хранит числа', 'по расписанию'], fill=.22, bold=True, size=11)
    s.box(500, 80, 130, 80, ['Grafana', 'графики'], fill=.14, bold=True, size=11)
    for y in (60, 140, 215):
        s.arrow(250, 120, 152, y, dash=True)
    s.text(205, 100, 'pull', size=11, weight='700')
    s.arrow(400, 120, 498, 120, 'PromQL')
    s.box(500, 190, 190, 40, ['ServiceMonitor: что опрашивать'], fill=.06, dash=True, size=10)
    s.arrow(595, 190, 360, 162, dash=True)
    s.text(350, 18, 'приборная панель вместо открывания капота на каждой кочке', size=12, weight='700')
    return s.html()


@scheme
def helm_capsule():
    s = Svg(700, 230, 'helm install: chart и values превращаются в манифесты в кластере; релиз записывается в журнал', pid='hc')
    s.box(10, 30, 130, 56, ['chart', 'шаблоны'], fill=.14, bold=True, size=12)
    s.box(10, 120, 130, 56, ['values', 'капсула'], fill=.22, bold=True, size=12)
    s.box(230, 70, 130, 70, ['helm', 'подстановка', '{{ }}'], fill=.1, bold=True, size=12)
    s.box(450, 70, 120, 70, ['манифесты', 'в кластере'], fill=.14, bold=True, size=11)
    s.box(590, 70, 100, 70, ['release', 'ревизия 1'], fill=.22, bold=True, size=11)
    s.arrow(140, 58, 228, 94)
    s.arrow(140, 148, 228, 116)
    s.arrow(360, 105, 448, 105)
    s.arrow(570, 105, 588, 105)
    s.text(350, 20, 'кофемашина: chart — машина, values — капсула, результат — чашка', size=12, weight='700')
    s.text(350, 206, 'каждый upgrade — новая ревизия; rollback возвращает прежнее содержимое', size=11, op=.85)
    return s.html()


@scheme
def template_form():
    s = Svg(700, 230, 'Шаблон с полями плюс values дают готовый YAML', pid='tf')
    s.box(10, 30, 210, 110, ['шаблон', 'replicas: {{ .Values.replicas }}', 'image: {{ .Values.image }}'], fill=.1, size=11)
    s.box(10, 160, 210, 50, ['values.yaml', 'replicas: 3   image: api:v1'], fill=.22, size=11)
    s.text(250, 100, '+', size=24, weight='700')
    s.box(300, 70, 150, 70, ['helm template', 'подстановка'], fill=.14, bold=True, size=12)
    s.arrow(222, 85, 298, 100)
    s.arrow(222, 185, 298, 120)
    s.arrow(450, 105, 498, 105)
    s.box(500, 30, 190, 150, ['готовый YAML', '', 'replicas: 3', 'image: api:v1'], fill=.08, size=12)
    s.text(350, 20, 'бланк с полями + заполненная анкета = готовый документ', size=12, weight='700')
    s.text(595, 200, 'это и читает Kubernetes', size=11, op=.85)
    return s.html()


@scheme
def umbrella_subcharts():
    s = Svg(700, 250, 'Umbrella chart coffeeshop с subcharts db, api, web; значения приходят сверху через имя subchart и global', pid='us')
    s.box(10, 10, 680, 230, [], fill=.03, dash=True)
    s.text(350, 34, 'umbrella chart  coffeeshop   (values.yaml + global)', size=13, weight='700')
    for i, (n, d) in enumerate([('coffeeshop-db', 'StatefulSet, PVC, Secret'), ('coffeeshop-api', 'Deployment, Service, Ingress'), ('coffeeshop-web', 'Deployment, Service, Ingress')]):
        x = 30 + i * 220
        s.box(x, 70, 200, 70, [n, d], fill=.14, bold=True, size=11)
        s.arrow(x + 100, 52, x + 100, 68)
    s.box(30, 170, 640, 50, ['global.dbPassword → попадает в db и api;   coffeeshop-api: { replicaCount: 3 } → только в api'], fill=.06, size=11)
    return s.html()


@scheme
def umbrella_house():
    s = Svg(700, 240, 'Итоговый релиз: один helm install ставит весь CoffeeShop в чистый кластер kind', pid='uh')
    s.box(10, 90, 130, 60, ['helm upgrade', '--install coffee', '--atomic'], fill=.22, bold=True, size=11)
    s.box(200, 20, 490, 200, [], fill=.04, dash=True)
    s.text(445, 40, 'кластер kind  /  namespace coffee', size=12, weight='700')
    s.box(215, 56, 140, 50, ['Traefik Ingress', 'shop.localhost'], fill=.14, size=11)
    s.box(215, 130, 140, 70, ['db (StatefulSet)', 'PVC, Secret', 'NetworkPolicy'], fill=.2, size=11)
    s.box(385, 56, 140, 50, ['web  ×2'], fill=.08, bold=True, size=12)
    s.box(385, 130, 140, 70, ['api  ×3 + HPA', 'probes, securityContext'], fill=.08, size=11)
    s.box(555, 90, 120, 60, ['Adminer', 'adminer.shop.…'], fill=.08, size=11)
    s.arrow(142, 120, 213, 80)
    s.arrow(355, 81, 383, 81)
    s.arrow(455, 108, 455, 128)
    s.arrow(385, 165, 357, 165)
    s.arrow(555, 120, 357, 160, dash=True)
    return s.html()


@scheme
def chart_repo():
    s = Svg(700, 220, 'Репозиторий chart’ов: архивы .tgz и опись index.yaml, раздаваемые по HTTP', pid='cr')
    s.box(10, 70, 130, 60, ['helm package', 'chart → .tgz'], fill=.14, bold=True, size=11)
    s.box(210, 30, 230, 140, [], fill=.04, dash=True)
    s.text(325, 50, 'репозиторий (папка / сервер)', size=12, weight='700')
    s.box(225, 66, 200, 34, ['coffeeshop-api-0.1.0.tgz'], fill=.08, size=11)
    s.box(225, 108, 200, 34, ['coffeeshop-db-0.1.0.tgz'], fill=.08, size=11)
    s.box(480, 70, 130, 60, ['index.yaml', 'опись версий'], fill=.22, bold=True, size=11)
    s.box(620, 70, 72, 60, ['helm repo', 'add'], fill=.1, size=10)
    s.arrow(140, 100, 208, 100)
    s.arrow(440, 100, 478, 100)
    s.arrow(610, 100, 618, 100)
    s.text(350, 200, 'полка с запакованными рецептами и опись; любой сервер, отдающий файлы, подойдёт', size=11, op=.85)
    return s.html()


@scheme
def final_task():
    s = Svg(700, 250, 'Итоговое задание: чистый кластер, один релиз, проверки по слоям', pid='ft')
    layers = [('Релиз', 'один helm install, --atomic'), ('Доступность', 'реплики, пробы, rolling update'), ('Данные', 'PVC, Secret, резервная копия'), ('Безопасность', 'securityContext, PSS, NetworkPolicy, RBAC'), ('Масштаб', 'HPA, requests, мониторинг'), ('Окружения', 'values-dev / prod, rollback')]
    for i, (a, b) in enumerate(layers):
        y = 14 + i * 38
        s.box(10, y, 160, 30, [a], fill=.16, bold=True, size=12)
        s.box(190, y, 330, 30, [b], fill=.06, size=11)
    s.box(550, 60, 140, 100, ['самопроверка', 'таблица', 'приёмки в ТЗ'], fill=.22, bold=True, size=12)
    s.arrow(520, 110, 548, 110)
    s.text(620, 190, 'схему релиза', size=11, op=.85)
    s.text(620, 206, 'нарисуешь ты сама —', size=11, op=.85)
    s.text(620, 222, 'это часть проверки', size=11, op=.85)
    return s.html()


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for name, f in S.items():
        if len(sys.argv) > 1 and name != sys.argv[1]:
            continue
        open(os.path.join(OUT, name + '.html'), 'w', encoding='utf-8').write(f())
        print('схема:', name)

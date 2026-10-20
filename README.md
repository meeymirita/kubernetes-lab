# Kubernetes Lab — Kubernetes и Helm с нуля

![Kubernetes](https://raw.githubusercontent.com/meeymirita/works-lab/main/images/kubernetes.png)

> **Относится к прежней 3-сессионной версии:** 24.09.2026 она была вычитана и исправлена. Что найдено и что поправлено — в [fixes/devops/kubernetes.md](https://github.com/meeymirita/lab-fixes/blob/main/devops/kubernetes.md) репозитория `lab-fixes`.

**Статус: ⬜ переписана 20.10.2026 (16 сессий, 108 шагов, ~64 ч); блоки в Docker не прогонялись — в «Ожидаемом результате» пометка «вывод не получен», построчно не вычитана, прохождения не было.** Предзнания (Docker и Traefik) и вход (`starter/` из шага 10.5 Traefik-лабы) — в [`kubernetes_lab_plan.md`](kubernetes_lab_plan.md). Исходники методички — `src/*.md` (сборка `python3 tools/build-manual.py kubernetes` из корня родительского репозитория, схемы — `src/schemes.py`).
**Сложность: средняя–высокая.** Нужны знания из Docker Lab и Traefik Lab — сюда переносится ровно их стек, поэтому новый домен не изучается, а сразу нужны настоящие понятия Kubernetes. Стек в Traefik-лабе теперь собирается как итоговая папка `starter/` (шаг 10.5); эта методичка (старая версия) приводит код `api/` целиком, так что её можно проходить и самостоятельно. `kind` и `kubectl` в Docker/Traefik-лабах не использовались — их нужно поставить отдельно перед стартом.

## О чём

Kubernetes и Helm с нуля на знакомом стеке: API + frontend + PostgreSQL + Adminer из Traefik Lab переезжают из `docker-compose.yml` в кластер kind. Архитектура и `kubectl`, Pod и Service, Deployment и обновления, Ingress (Traefik), хранение данных и StatefulSet, ConfigMap и Secret, пробы и ресурсы, RBAC и NetworkPolicy, автомасштабирование, Prometheus и Grafana, затем весь Helm (chart, шаблоны, репозитории, релизы, umbrella chart) и Kustomize для сравнения. Домен нарочно не новый, чтобы видеть именно то, что меняется при переходе к оркестрации.

## Стек

Kubernetes v1.37.0 (kind v0.33, образ узла `kindest/node:v1.37.0`) + kubectl + Helm 4 + Traefik v3.7 как Ingress-контроллер + kube-prometheus-stack. Приложение — то же, что в Traefik Lab: Node.js API + статический frontend + PostgreSQL 18 + Adminer. Запуском эта версия пока не проверена.

## Формат

Методичка [`kubernetes.html`](kubernetes.html) ([открыть на сайте](https://anitech.meeymirita.ru/works/kubernetes.html)) — открывается в браузере, прогресс по чекбоксам сохраняется локально.

## Локальный кластер

Весь лаб — на [kind](https://kind.sigs.k8s.io/) (Kubernetes IN Docker): настоящий control plane и worker-узлы, только упакованные в Docker-контейнеры вместо отдельных машин. Тот же `kubectl`, те же объекты, тот же API, что и в проде.

## Что внутри (16 сессий)

- **Сессия 1 · Азбука и окружение** — зачем оркестратор, kind-кластер из трёх узлов, kubectl и helm, проверка starter/
- **Сессия 2 · Архитектура и объекты** — путь `apply` по компонентам, reconcile, метки и селекторы, API-группы
- **Сессия 3 · Pod и Service** — Pod, фазы, logs/exec, Service и DNS, образ в kind
- **Сессия 4 · Deployment и обновления** — ReplicaSet, масштабирование, rolling update, rollout/undo, Recreate
- **Сессия 5 · Сети и Ingress** — типы Service, DNS кластера, Traefik как Ingress-контроллер, Ingress и IngressRoute, порты kind
- **Сессия 6 · Хранение данных** — PV/PVC/StorageClass, PostgreSQL 18, StatefulSet, pg_dump и CronJob
- **Сессия 7 · Секреты и конфигурация** — ConfigMap, Secret, base64 ≠ шифрование, весь стек CoffeeShop вместе
- **Сессия 8 · Эксплуатация и диагностика** — namespace и квоты, пробы, requests/limits, Job, k9s, таблица диагностики, Production Hell 1
- **Сессия 9 · Безопасность и сеть-политики** — RBAC, ServiceAccount, securityContext, Pod Security Standards, NetworkPolicy, цепочка поставки
- **Сессия 10 · Автомасштабирование** — metrics-server, HPA под нагрузкой, VPA и Cluster Autoscaler (обзор)
- **Сессия 11 · Наблюдаемость** — kubectl top, kube-prometheus-stack, ServiceMonitor, Grafana, логи
- **Сессия 12 · Helm, основы** — chart, release, свой chart для API, install/upgrade, отладка YAML
- **Сессия 13 · Шаблоны Helm** — Go template, функции, if/with/range, _helpers, chart для БД, subcharts
- **Сессия 14 · Репозитории, релизы, окружения** — helm package и репозиторий, atomic/rollback, lint/diff/test, values-dev/prod, секреты
- **Сессия 15 · Итоговый проект** — umbrella chart CoffeeShop, values-prod, Kustomize, Production Hell 2
- **Сессия 16 · Итоговое задание** — продакшн-релиз по ТЗ без решения

## Лицензия и авторство

Код — MIT, тексты — CC BY 4.0, обложки и иллюстрации не покрыты (см. [LICENSE](LICENSE)). Кто что сделал: [NOTICE](NOTICE).

---

Часть сборного репозитория лабораторных работ — [anitech-performance](https://github.com/meeymirita/anitech-performance).

## План развития

Исходный план — [`kubernetes_lab_plan.md`](kubernetes_lab_plan.md). Методичка написана по нему 19–20.10.2026. Дальше: прогон всех блоков в Docker-в-Docker и подстановка настоящего вывода, построчная вычитка, схемы проверить глазами.

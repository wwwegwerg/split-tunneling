# Split tunneling

Списки доменов российских сервисов, IP России и Беларуси и сетей Telegram.

Идея — [Davoyan/mihomo-rule-sets](https://github.com/Davoyan/mihomo-rule-sets).

| Набор | Содержание |
| --- | --- |
| ru-domains | Домены российских сервисов |
| ru-ips | Подсети RU/BY и выбранных организаций |
| telegram-domains | Дополнительные домены из списка Davoyan, включая сторонние клиенты |
| telegram-ips | Подсети Telegram и сети AS1273/AS44893 |

## Приложения

Файлы доступны по постоянной ссылке:

```text
https://github.com/wwwegwerg/split-tunneling/releases/latest/download/ИМЯ-ФАЙЛА
```

В Mihomo и Shadowrocket правила Telegram используют VPN-политику и располагаются раньше RU.
IP из набора Telegram исключены из RU во всех форматах: пересекающиеся подсети не отправят
Telegram напрямую. AS1273/AS44893 захватывают также адреса сторонних сервисов.

### Mihomo

Домены — `.mihomo.yaml` с `behavior: classical` и `format: yaml`;
IP — `.mihomo.mrs` с `behavior: ipcidr` и `format: mrs`. Например:

```yaml
rule-providers:
  ru-domains:
    type: http
    behavior: classical
    format: yaml
    interval: 86400
    url: https://github.com/wwwegwerg/split-tunneling/releases/latest/download/ru-domains.mihomo.yaml
rules:
  - RULE-SET,ru-domains,DIRECT
```

### Shadowrocket

Секция `[Rule]` конфигурации:

```ini
[Rule]
RULE-SET,https://github.com/wwwegwerg/split-tunneling/releases/latest/download/telegram-domains.shadowrocket.list,PROXY
RULE-SET,https://github.com/wwwegwerg/split-tunneling/releases/latest/download/telegram-ips.shadowrocket.list,PROXY
RULE-SET,https://github.com/wwwegwerg/split-tunneling/releases/latest/download/ru-domains.shadowrocket.list,DIRECT
RULE-SET,https://github.com/wwwegwerg/split-tunneling/releases/latest/download/ru-ips.shadowrocket.list,DIRECT
FINAL,PROXY
```

`PROXY` использует выбранный на главном экране сервер. Telegram идёт через него,
RU — напрямую, остальные адреса — через `FINAL,PROXY`.

1. В **Config** у локальной конфигурации: **Edit Plain Text** → замена секции `[Rule]`
   примером выше → сохранение.
2. В меню этой конфигурации: **Use Config**. Конфигурация становится активной,
   а удалённые RULE-SET скачиваются и компилируются.
3. На главном экране: **Global Routing → Config**, выбор сервера и включение подключения.
   В режиме **Config** маршрутизация определяется правилами.

Для ручного обновления списков: **Config → активная конфигурация → Use Config / Compile Config**.
Автообновление ресурсов конфигурации включается отдельно в настройках Shadowrocket;
интервал для ежедневного обновления — 1 день. На iOS нужен доступ Shadowrocket
к **Background App Refresh**.
Постоянная ссылка `latest/download` ведёт на свежий релиз, но не включает автообновление клиента.

### AmneziaVPN

Нужна версия 5.0.1.5 или новее. `ru-ips.amnezia.json` импортируется в список сайтов
раздельного туннелирования для обхода VPN. `telegram-ips.amnezia.json` можно
использовать отдельно в режиме «только адреса из списка через VPN».
Изменения применяются после включения раздельного туннелирования и переподключения VPN.

Это ручной импорт, не подписка. Экспорт содержит только IPv4; совпадения по имени
домена (`full`/`domain`/`keyword`) не переносимы в Amnezia. Раздельное туннелирование IP недоступно
в Amnezia Free. [Инструкция](https://docs.amnezia.org/documentation/instructions/vpn-split-tunneling/).

**Отдельный AmneziaWG:** JSON-импорт отсутствует; `AllowedIPs` перечисляет адреса
через туннель. Для обхода RU нужен обратный список и настройка конкретного профиля.
При использовании AWG внутри AmneziaVPN или Mihomo подходят экспорты этих приложений.

## Нейтральные списки

`.txt` с доменами: `full:` — точное совпадение, `domain:` — домен с поддоменами,
`keyword:` — подстрока. IP-файлы содержат CIDR, по одной подсети на строку.
Политика `DIRECT`/`PROXY` выбирается в клиенте.

[Источники и лицензии](SOURCES.md).

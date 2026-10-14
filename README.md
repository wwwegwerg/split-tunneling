# Split tunneling

Списки доменов российских сервисов, IP России и Беларуси и сетей Telegram.
Обновляются автоматически ежедневно.

Идея — [Davoyan/mihomo-rule-sets](https://github.com/Davoyan/mihomo-rule-sets).

| Набор | Содержание |
| --- | --- |
| ru-domains | Домены российских сервисов |
| ru-ips | Подсети RU/BY и выбранных организаций |
| telegram-domains | Домены Telegram и дополнения Davoyan |
| telegram-ips | Подсети Telegram и сети AS1273/AS44893 |

## Приложения

Файлы доступны по постоянной ссылке:

```text
https://github.com/wwwegwerg/split-tunneling/releases/latest/download/ИМЯ-ФАЙЛА
```

В Mihomo и Shadowrocket правила Telegram используют VPN-политику и располагаются раньше RU.
Адреса Telegram исключены из RU, чтобы не попадать под прямое подключение.
AS1273/AS44893 захватывают также адреса сторонних сервисов.

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

```ini
[Rule]
RULE-SET,https://github.com/wwwegwerg/split-tunneling/releases/latest/download/telegram-domains.shadowrocket.list,PROXY
RULE-SET,https://github.com/wwwegwerg/split-tunneling/releases/latest/download/telegram-ips.shadowrocket.list,PROXY
RULE-SET,https://github.com/wwwegwerg/split-tunneling/releases/latest/download/ru-domains.shadowrocket.list,DIRECT
RULE-SET,https://github.com/wwwegwerg/split-tunneling/releases/latest/download/ru-ips.shadowrocket.list,DIRECT
FINAL,PROXY
```

Автообновление списков в Shadowrocket настраивается отдельно.
На iOS требуется **Background App Refresh**.

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

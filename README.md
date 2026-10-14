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

Фрагмент для добавления в существующую конфигурацию:

```yaml
mode: rule

rule-providers:
  telegram-domains:
    type: http
    behavior: classical
    format: yaml
    interval: 86400
    url: https://github.com/wwwegwerg/split-tunneling/releases/latest/download/telegram-domains.mihomo.yaml
  telegram-ips:
    type: http
    behavior: ipcidr
    format: mrs
    interval: 86400
    url: https://github.com/wwwegwerg/split-tunneling/releases/latest/download/telegram-ips.mihomo.mrs
  ru-domains:
    type: http
    behavior: classical
    format: yaml
    interval: 86400
    url: https://github.com/wwwegwerg/split-tunneling/releases/latest/download/ru-domains.mihomo.yaml
  ru-ips:
    type: http
    behavior: ipcidr
    format: mrs
    interval: 86400
    url: https://github.com/wwwegwerg/split-tunneling/releases/latest/download/ru-ips.mihomo.mrs

rules:
  - RULE-SET,telegram-domains,PROXY
  - RULE-SET,telegram-ips,PROXY
  - RULE-SET,ru-domains,DIRECT
  - RULE-SET,ru-ips,DIRECT
  - MATCH,PROXY
```

Для `PROXY` нужна одноимённая группа или прокси в конфигурации.

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

AmneziaVPN 5.0.1.5 и новее. JSON импортируется в список сайтов раздельного туннелирования.

| Файл | Режим |
| --- | --- |
| [ru-ips.amnezia.json](https://github.com/wwwegwerg/split-tunneling/releases/latest/download/ru-ips.amnezia.json) | Адреса списка без VPN, остальные через VPN |
| [telegram-ips.amnezia.json](https://github.com/wwwegwerg/split-tunneling/releases/latest/download/telegram-ips.amnezia.json) | Только адреса списка через VPN |

Обновление — повторным импортом; изменения применяются после переподключения VPN.
Списки содержат только IPv4. В Amnezia Free раздельное туннелирование IP недоступно.
[Инструкция приложения](https://docs.amnezia.org/documentation/instructions/vpn-split-tunneling/).

Списки подходят для протокола AmneziaWG внутри AmneziaVPN.
Отдельное приложение AmneziaWG не поддерживает этот JSON-импорт.

## Нейтральные списки

`.txt` с доменами: `full:` — точное совпадение, `domain:` — домен с поддоменами,
`keyword:` — подстрока. IP-файлы содержат CIDR, по одной подсети на строку.
Политика `DIRECT`/`PROXY` выбирается в клиенте.

[Источники и лицензии](SOURCES.md).

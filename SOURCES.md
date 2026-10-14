# Источники

Основа источников и фильтров —
[Davoyan/mihomo-rule-sets](https://github.com/Davoyan/mihomo-rule-sets).
URL и критерии отбора находятся в
[config/sources.toml](https://github.com/wwwegwerg/split-tunneling/blob/main/config/sources.toml).

IP собираются из IPinfo Lite, MaxMind GeoLite Country и геофидов.
Кроме подсетей RU/BY, включены сети выбранных организаций независимо от географии.

IP address data powered by [IPinfo](https://ipinfo.io/lite).
This product includes GeoLite Data created by [MaxMind](https://www.maxmind.com).
Данные фильтруются по стране и организации, объединяются, дедуплицируются и преобразуются
в форматы клиентов. Собственные изменения в IP-списках —
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
[GeoLite EULA](https://www.maxmind.com/en/geolite/eula) требует удаления старых данных
в течение 30 дней после выхода обновления; устаревшие локальные копии тоже нужно удалять.

Доменные списки: MetaCubeX, itdoginfo и hydraponique. Legacy сохраняет записи,
удалённые hydraponique после проверки покрытия своим IP-списком; позже Davoyan
добавлял туда ручные правила.

blocked-domains — [itdog Russia inside](https://github.com/itdoginfo/allow-domains#russia-inside):
заблокированные ресурсы и сервисы, ограничивающие доступ с российских IP.

Геосайты MetaCubeX происходят из v2fly/domain-list-community; ASN-списки — из GeoLite2-ASN.
MIT-notice hydraponique и v2fly сохранён в `third-party-notices.txt`.
В используемых репозиториях itdoginfo и Davoyan, ветке данных MetaCubeX и файлах геофидов
отдельная лицензия данных не объявлена.

Домены Telegram объединяют набор MetaCubeX (включая `t.me` и `telegram.org`)
и дополнения Davoyan, содержащие также домены сторонних клиентов.
IP Telegram включают официальный CIDR-список, дополнения Davoyan и сети AS1273/AS44893.
AS1273/AS44893 содержат также инфраструктуру, не принадлежащую Telegram.

Исправление сохранения CIDR вошло в 5.0.1.5 ([#2973](https://github.com/amnezia-vpn/amnezia-client/pull/2973)).

Код — [MIT](https://github.com/wwwegwerg/split-tunneling/blob/main/LICENSE).
Лицензия кода не заменяет условия исходных данных.

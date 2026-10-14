# Источники

Состав источников и фильтры перенесены из
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

Геосайты MetaCubeX происходят из v2fly/domain-list-community; ASN-списки — из GeoLite2-ASN.
MIT-notice hydraponique и v2fly сохранён в `third-party-notices.txt`.
В используемых репозиториях itdoginfo и Davoyan, ветке данных MetaCubeX и файлах геофидов
отдельная лицензия данных не объявлена.

Telegram включает официальный CIDR-список и дополнения Davoyan.
Домены сторонних клиентов приходят из скачиваемого списка Davoyan;
собственных дополнений для них нет. IP из итогового набора Telegram вычитаются из RU
во всех форматах, с сохранением остальных адресов содержащих подсетей.
AS1273/AS44893 содержат также инфраструктуру, не принадлежащую Telegram.

Исправление сохранения CIDR вошло в 5.0.1.5 ([#2973](https://github.com/amnezia-vpn/amnezia-client/pull/2973)).

Код — [MIT](https://github.com/wwwegwerg/split-tunneling/blob/main/LICENSE).
Лицензия кода не заменяет условия исходных данных.

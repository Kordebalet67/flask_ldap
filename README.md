✅ Решение: IIS + Windows Authentication (уже в вашей Windows)
IIS не требует настройки AD, если использовать NTLM (работает "из коробки" в домене). Браузер автоматически отправит тикет, IIS проверит его у контроллера домена и передаст имя пользователя в Flask.
📦 Шаг 1. Включите IIS (2 минуты, через PowerShell от админа)

powershell
1

🐍 Шаг 2. Подключите Python к IIS

bash
1
2

Команда выведет путь к обработчику, например: C:\Python310\python.exe|C:\Python310\lib\site-packages\wfastcgi.py
🌐 Шаг 3. Создайте сайт в IIS

    Откройте IIS Manager → Sites → Add Website
    Site name: flask-sso
    Physical path: папка с вашим app.py
    Binding: http, порт 5000, IP All Unassigned
    Нажмите OK

🔐 Шаг 4. Включите Windows Auth в IIS

    Выберите созданный сайт → двойной клик Authentication
    Windows Authentication: Enable
    Anonymous Authentication: Disable
    Перезапустите сайт: Manage Website → Restart

💻 Обновлённый app.py (читает учётку из IIS)

python
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34

🔑 Почему это работает без настройки AD?

    NTLM не требует SPN или krb5.keytab. IIS просто пересылает challenge-response между браузером и контроллером домена.
    Браузер автоматически отправляет учётку, если сайт находится в зоне Local Intranet. Это выполняется по умолчанию для:
        http://имя_сервера (без точек в имени)
        http://127.0.0.1 или http://localhost
    Если имя сервера содержит точки (например, http://app.corp.local), добавьте его в зону Intranet через групповые политики или локальный реестр.


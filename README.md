✅ Решение: IIS + Windows Authentication (уже в вашей Windows)
IIS не требует настройки AD, если использовать NTLM (работает "из коробки" в домене). Браузер автоматически отправит тикет, IIS проверит его у контроллера домена и передаст имя пользователя в Flask.
📦 Шаг 1. Включите IIS (2 минуты, через PowerShell от админа)

powershell
dism /online /enable-feature /featurename:IIS-WebServerRole /featurename:IIS-WebServer /featurename:IIS-CommonHttpFeatures /featurename:IIS-HttpErrors /featurename:IIS-ApplicationDevelopment /featurename:IIS-CGI /featurename:IIS-WindowsAuthentication

🐍 Шаг 2. Подключите Python к IIS

bash
pip install wfastcgi
wfastcgi-enable  # запускать от имени Администратора

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
from flask import Flask, request, session, redirect, url_for, flash
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(32))

@app.route('/')
def index():
    # IIS передаёт имя пользователя в переменную окружения
    remote_user = request.environ.get('REMOTE_USER')
    
    if not remote_user:
        return 'SSO не сработал. Убедитесь, что ПК в домене, а сайт открыт по http://имя_сервера', 401

    # Убираем домен: DOMAIN\user или user@DOMAIN.LOCAL → user
    username = remote_user.split('\\')[-1].split('@')[0]
    session['username'] = username
    flash(f'Автоматический вход: {username}', 'success')
    
    return f'''
        <h2>Добро пожаловать, {username}!</h2>
        <p>Аутентификация: Windows SSO (через IIS)</p>
        <a href="/logout">Выйти</a>
    '''

@app.route('/logout')
def logout():
    session.clear()
    # При SSO "выход" только очищает сессию приложения
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Запускать только через IIS! flask run отключён.
    print("Приложение запускается через IIS. Откройте http://localhost:5000")

🔑 Почему это работает без настройки AD?

    NTLM не требует SPN или krb5.keytab. IIS просто пересылает challenge-response между браузером и контроллером домена.
    Браузер автоматически отправляет учётку, если сайт находится в зоне Local Intranet. Это выполняется по умолчанию для:
        http://имя_сервера (без точек в имени)
        http://127.0.0.1 или http://localhost
    Если имя сервера содержит точки (например, http://app.corp.local), добавьте его в зону Intranet через групповые политики или локальный реестр.


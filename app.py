from flask import Flask, request, render_template, redirect, url_for, session, flash
from ldap3 import Server, Connection, ALL
from ldap3.core.exceptions import LDAPBindError

app = Flask(__name__)
# ⚠️ В продакшене обязательно замените на случайную строку!
app.secret_key = 'замените_на_длинный_секретный_ключ'

# 🔧 Настройки LDAP (адаптируйте под вашу инфраструктуру)
LDAP_SERVER = 'ldap://internet.loc'  # или ldaps:// для TLS
# Формат DN пользователя. Зависит от типа LDAP:
# • OpenLDAP: 'uid={username},ou=people,dc=example,dc=com'
# • Active Directory: '{username}@example.com' или 'CN={username},OU=Users,DC=example,DC=com'
LDAP_USER_DN_TEMPLATE = '{username}@internet.loc'

@app.route('/')
def index():
    if 'username' in session:
        return f'''
            <h2>Добро пожаловать, {session["username"]}!</h2>
            <a href="/logout">Выйти</a>
        '''
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Заполните все поля', 'warning')
            return render_template('login.html')

        user_dn = LDAP_USER_DN_TEMPLATE.format(username=username)

        try:
            server = Server(LDAP_SERVER, get_info=ALL)
            # auto_bind=False позволяет нам обработать результат вручную
            conn = Connection(server, user=user_dn, password=password, auto_bind=False)
            
            if conn.bind():
                conn.unbind()
                session['username'] = username
                flash('Вход выполнен успешно!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Неверный логин или пароль', 'danger')

        except LDAPBindError:
            # Стандартное исключение при неверных учетных данных
            flash('Неверный логин или пароль', 'danger')
        except Exception as e:
            flash(f'Ошибка подключения к LDAP: {str(e)}', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    debug=True # только для разработки!
    app.run(debug=True)
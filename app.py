import os
import platform
from flask import Flask, request, render_template, redirect, url_for, session, flash
from ldap3 import Server, Connection, ALL, SUBTREE, NTLM, SASL, GSSAPI
from ldap3.core.exceptions import LDAPBindError, LDAPException
import winkerberos
import win32security
import win32api

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change_me_32_chars_min')

LDAP_CONFIG = {
    'server': 'ldap://dc01.internet.loc',
    'server_fqdn': 'dc01.internet.loc',
    'use_ssl': False,
    'base_dn': 'DC=internet,DC=loc',
    'user_template_ad': '{username}@internet.loc',
    'auth_type': 'auto',
}

def get_auth_method():
    if LDAP_CONFIG['auth_type'] != 'auto':
        return LDAP_CONFIG['auth_type']
    return 'ntlm' if platform.system() == 'Windows' else 'gssapi'

def get_user_dn(username):
    return LDAP_CONFIG['user_template_ad'].format(username=username)

@app.route('/')
def index():
    if 'username' in session:
        return f"""
            <h2>Добро пожаловать, {session['username']}!</h2>
            <p>Auth: {session.get('auth_method')}</p>
            <a href="/logout">Выйти</a>
        """
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Заполните все поля', 'warning')
            return render_template('login.html', platform=platform.system())

        user_dn = get_user_dn(username)
        auth_method = get_auth_method()

        try:
            server = Server(LDAP_CONFIG['server'], get_info=ALL, use_ssl=LDAP_CONFIG['use_ssl'])
            conn = Connection(
                server,
                user=user_dn,
                password=password,
                authentication=NTLM if auth_method == 'ntlm' else None,
                auto_bind=False
            )

            if conn.bind():
                conn.unbind()
                session['username'] = username
                session['auth_method'] = 'manual'
                flash('Вход выполнен успешно!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Неверный логин или пароль', 'danger')

        except LDAPBindError:
            flash('Неверный логин или пароль', 'danger')
        except Exception as e:
            flash(f'Ошибка: {str(e)}', 'danger')

    return render_template('login.html', platform=platform.system())

@app.route('/login_auto', methods=['POST'])
def login_auto():
    if platform.system() != 'Windows':
        flash('Автовход доступен только на Windows', 'warning')
        return redirect(url_for('login'))

    try:
        # Получаем текущего пользователя Windows
        token = win32security.OpenProcessToken(
            win32api.GetCurrentProcess(),
            win32security.TOKEN_QUERY
        )
        user_info = win32security.GetTokenInformation(token, win32security.TokenUser)
        sid = user_info[0]
        username, domain, _ = win32security.LookupAccountSid(None, sid)

        # ВАЖНО: правильный SPN
        spn = "ldap/DC.internet.loc"

        result, context = winkerberos.authGSSClientInit(
            spn,
            gssflags=winkerberos.GSS_C_MUTUAL_FLAG | winkerberos.GSS_C_SEQUENCE_FLAG
        )

        winkerberos.authGSSClientStep(context, "")
        kerberos_token = winkerberos.authGSSClientResponse(context)

        # LDAP bind через GSSAPI
        server = Server("ldap://DC.internet.loc", get_info=ALL)
        conn = Connection(
            server,
            authentication=SASL,
            sasl_mechanism=GSSAPI,
            auto_bind=True
        )

        session['username'] = username
        session['domain'] = domain
        session['auth_method'] = 'sso_windows'
        flash(f'Автовход выполнен: {domain}\\{username}', 'success')
        return redirect(url_for('index'))

    except Exception as e:
        flash(f'Ошибка SSO: {str(e)}', 'danger')
        return redirect(url_for('login'))


@app.route('/login_auto_gssapi', methods=['POST'])
def login_auto_gssapi():
    if platform.system() == 'Windows':
        flash('GSSAPI доступен только на Linux/macOS', 'info')
        return redirect(url_for('login'))

    try:
        username = os.environ.get('USER') or os.getlogin()
        server = Server(LDAP_CONFIG['server'], get_info=ALL, use_ssl=LDAP_CONFIG['use_ssl'])

        conn = Connection(
            server,
            authentication=SASL,
            sasl_mechanism=GSSAPI,
            auto_bind=True
        )

        if conn.bound:
            conn.unbind()
            session['username'] = username
            session['auth_method'] = 'sso_gssapi'
            flash(f'GSSAPI вход выполнен: {username}', 'success')
            return redirect(url_for('index'))

    except Exception as e:
        flash(f'Ошибка GSSAPI: {str(e)}', 'danger')

    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1')

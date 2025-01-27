from flask import Flask, redirect, url_for, session, render_template, flash, request
from authlib.integrations.flask_client import OAuth
from functools import wraps
import yaml
import logging
import sys

def load_config(file_path='config.yaml'):
    """환경 변수 로드"""
    with open(file_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

def setup_logging():
    """로깅 설정"""
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    logger = logging.getLogger('oauth_debug')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    
    app.logger.setLevel(logging.DEBUG)
    app.logger.handlers.clear()
    app.logger.addHandler(console_handler)
    
    return logger

def handle_errors(f):
    """에러 처리 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            app.logger.error(f"Error in {f.__name__}: {str(e)}", exc_info=True)
            flash("처리 중 문제가 발생했습니다. 다시 시도해주세요.", "danger")
            return redirect(url_for('index'))
    return decorated_function

# 환경 변수 로드
config = load_config('config.yaml')

app = Flask(__name__)
app.secret_key = config['flask']['secret_key']

# 세션 보안 설정
app.config.update(
    SESSION_COOKIE_SECURE=False,  # 개발환경에서는 False
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=3600  # 1시간
)

# OAuth 초기화
oauth = OAuth(app)
oauth.register(
    name='oidc',
    authority=config['cognito']['authority'],
    server_metadata_url=config['cognito']['metadata_url'],
    client_id=config['cognito']['client_id'],
    client_secret=config['cognito']['client_secret'],
    client_kwargs={
        'scope': 'openid email'
    }
)

# 로거 설정
logger = setup_logging()

@app.route('/')
@handle_errors
def index():
    """메인 페이지"""
    user = session.get('user')
    return render_template('index.html', user=user)

@app.route('/login')
@handle_errors
def login():
    app.logger.debug('Login process started')
    return oauth.oidc.authorize_redirect('http://localhost:5000/authorize') # URI 변경 가능

@app.route('/authorize') # login 쪽 URI랑 맞춰야 함
@handle_errors
def authorize():
    app.logger.debug('Authorization process started')
    app.logger.debug(f"Authorization request args: {request.args}")
    token = oauth.oidc.authorize_access_token()
    app.logger.debug(f"Token received")
    app.logger.debug(f"Token response: {token}")

    user = token['userinfo']
    session['user'] = user
    return redirect(url_for('index'))

@app.route('/logout')
@handle_errors
def logout():
    """로그아웃"""
    app.logger.debug("Logging out user")
    session.pop('user', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

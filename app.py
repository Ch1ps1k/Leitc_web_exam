from flask import Flask, render_template, request, redirect, url_for, make_response, jsonify
import sqlite3
import hashlib
import os

app = Flask(__name__)
app.secret_key = 'super_secret_key_123'
DATABASE = 'users.db'

def init_db():
    """Инициализация базы данных с уязвимой структурой"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Создаем таблицу пользователей (уязвимая структура)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Добавляем тестового пользователя Administrator
    try:
        c.execute("INSERT OR IGNORE INTO users (username, password) VALUES ('Administrator', 'admin123')")
        conn.commit()
    except:
        pass
    
    conn.close()

def md5_hash(text):
    """Простое MD5 хеширование (уязвимо!)"""
    return hashlib.md5(text.encode()).hexdigest()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        email = request.form.get('email', '')
        
        if username and password:
            try:
                conn = sqlite3.connect(DATABASE)
                c = conn.cursor()
                
                # УЯЗВИМЫЙ КОД - SQL инъекция возможна!
                query = f"INSERT INTO users (username, password, email) VALUES ('{username}', '{md5_hash(password)}', '{email}')"
                
                c.execute(query)
                conn.commit()
                
                # Устанавливаем cookie
                resp = make_response(redirect(url_for('profile')))
                resp.set_cookie('user_id', str(c.lastrowid))
                resp.set_cookie('username', username)
                return resp
                
            except sqlite3.IntegrityError:
                return render_template('register.html', error='Пользователь уже существует')
            except Exception as e:
                return render_template('register.html', error=f'Ошибка: {str(e)}')
            finally:
                conn.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        if username and password:
            try:
                conn = sqlite3.connect(DATABASE)
                c = conn.cursor()
                
                # КРИТИЧЕСКАЯ УЯЗВИМОСТЬ - SQL инъекция!
                query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{md5_hash(password)}'"
                
                c.execute(query)
                user = c.fetchone()
                
                if user:
                    # Устанавливаем cookie
                    resp = make_response(redirect(url_for('profile')))
                    resp.set_cookie('user_id', str(user[0]))
                    resp.set_cookie('username', user[1])
                    return resp
                else:
                    return render_template('login.html', error='Неверный логин или пароль')
                    
            except Exception as e:
                return render_template('login.html', error=f'Ошибка: {str(e)}')
            finally:
                conn.close()
    
    return render_template('login.html')

@app.route('/profile')
def profile():
    # Проверяем авторизацию через cookie
    username = request.cookies.get('username')
    user_id = request.cookies.get('user_id')
    
    if not username or not user_id:
        return redirect(url_for('login'))
    
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        # Ещё одна уязвимость - SQLi через user_id
        query = f"SELECT * FROM users WHERE id = {user_id}"
        c.execute(query)
        user = c.fetchone()
        
        if user:
            return render_template('profile.html', username=username, user=user)
        else:
            return redirect(url_for('login'))
            
    except Exception as e:
        return f'Ошибка: {str(e)}'
    finally:
        conn.close()

@app.route('/search', methods=['GET'])
def search():
    """Уязвимый поиск пользователей"""
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({'error': 'No query provided'})
    
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        # Уязвимый поиск - SQL инъекция!
        sql = f"SELECT id, username, email FROM users WHERE username LIKE '%{query}%' OR email LIKE '%{query}%'"
        c.execute(sql)
        results = c.fetchall()
        
        return jsonify({
            'query': sql,
            'results': [{'id': r[0], 'username': r[1], 'email': r[2]} for r in results]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})
    finally:
        conn.close()

@app.route('/api/users', methods=['GET'])
def get_users():
    """API для получения пользователей (уязвимо!)"""
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        # Уязвимый запрос - можно добавить UNION и т.д.
        limit = request.args.get('limit', '10')
        query = f"SELECT * FROM users LIMIT {limit}"
        
        c.execute(query)
        users = c.fetchall()
        
        return jsonify({
            'users': [
                {
                    'id': u[0],
                    'username': u[1],
                    'password': u[2],  # Пароли в открытом виде!
                    'email': u[3]
                } for u in users
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})
    finally:
        conn.close()

@app.route('/logout')
def logout():
    resp = make_response(redirect(url_for('index')))
    resp.delete_cookie('username')
    resp.delete_cookie('user_id')
    return resp

@app.route('/debug')
def debug():
    """Страница отладки для тестирования"""
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        # Показываем всех пользователей
        c.execute("SELECT * FROM users")
        users = c.fetchall()
        
        # Показываем таблицы
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = c.fetchall()
        
        conn.close()
        
        return jsonify({
            'tables': [t[0] for t in tables],
            'users': [
                {
                    'id': u[0],
                    'username': u[1],
                    'password': u[2],
                    'email': u[3]
                } for u in users
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

# Инициализация БД при старте
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
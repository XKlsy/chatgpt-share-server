from flask import Flask, request, Response, jsonify
from flask import Flask, request, make_response, jsonify, redirect
import requests
import pymysql
import pymysql.cursors
from datetime import datetime
from urllib.parse import quote
import json
import re
import os
import chardet
from datetime import datetime, timedelta
app = Flask(__name__)
convid = None
# 目标服务器的地址
TARGET_URL = 'http://23.224.111.139:8300'
AUTH_TARGET_URL = 'http://23.224.111.139:8300'

# 数据库配置
DB_CONFIG = {
    'host': '23.224.111.139',
    'port': 3306,
    'user': 'xychatai',
    'password': 'Xk1206..',
    'db': 'chatgpt-share-test',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}
ORIGINAL_LOGIN_URL = 'http://23.224.111.139:8300/auth/login'
TARGET_SERVER = 'http://23.224.111.139:8300'
@app.route('/file-<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def file_proxy(subpath):
    try:
        # 使用 Flask 的 request.args 来获取完整的查询字符串
        query_string = request.query_string.decode('utf-8')
        target_url = f'https://file.imyai.top/file-{subpath}'
        if query_string:
            target_url += '?' + query_string

        # 打印出最终的目标 URL 以便调试
        print("Target URL:", target_url)

        method = request.method
        data = request.get_data()
        headers = {key: value for key, value in request.headers.items() if key.lower() != 'host'}
        cookies = request.cookies

        response = requests.request(method, target_url, headers=headers, data=data, cookies=cookies, allow_redirects=True)

        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection', 'keep-alive']
        headers = [(name, value) for (name, value) in response.headers.items() if name.lower() not in excluded_headers]

        resp = Response(response.content, status=response.status_code, headers=headers)

        # 设置响应中的cookie
        if 'set-cookie' in response.headers:
            resp.headers['Set-Cookie'] = response.headers['Set-Cookie']

        return resp
    except Exception as e:
        print("Error:", e)
        return str(e), 500
@app.route('/public-api/gizmos/discovery/mine', methods=['GET', 'POST'])
def monitor_discovery_mine():
    # 获取请求头中的Authorization
    auth_header = request.headers.get('Authorization')

    # 提取token
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]

        # 构建文件路径
        file_path = f'mine{token}.txt'

        # 检查文件是否存在并且不为空
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            # 返回预定义的JSON响应
            return jsonify({
                "info": {
                    "id": "mine",
                    "title": "我的 GPT",
                    "description": None,
                    "display_type": "none",
                    "display_group": None,
                    "locale": None
                },
                "list": {
                    "items": [],
                    "cursor": None
                }
            })

        # 如果文件存在且不为空，读取文件内容
        with open(file_path, 'r') as file:
            ids = file.readlines()

        responses = []
        for id in ids:
            id = id.strip()  # 去除行末尾的换行符
            if id:
                target_url = f'http://127.0.0.1:8300/backend-api/gizmos/{id}'
                headers = {key: value for key, value in request.headers if key.lower() != 'host'}
                cookies = request.cookies

                # 转发请求
                response = requests.get(target_url, headers=headers, cookies=cookies)

                # 检查响应的Content-Type是否为application/json
                if response.headers.get('Content-Type') == 'application/json':
                    try:
                        data = response.json()
                    except ValueError as e:
                        return jsonify({"error": f"Failed to parse JSON response from {target_url}: {str(e)}", "response_text": response.text}), 500

                    transformed_data = {
                        "resource": {
                            "gizmo": data["gizmo"],
                            "tools": data.get("tools", []),
                            "files": data.get("files", []),
                            "product_features": data.get("product_features", {})
                        },
                        "flair": {
                            "kind": "sidebar_keep"
                        }
                    }
                    responses.append(transformed_data)
                else:
                    return jsonify({"error": f"Invalid Content-Type received from {target_url}", "content_type": response.headers.get('Content-Type')}), 500

        return jsonify({
            "info": {
                "id": "mine",
                "title": "我的 GPT",
                "description": None,
                "display_type": "none",
                "display_group": None,
                "locale": None
            },
            "list": {
                "items": responses,
                "cursor": None
            }
        })
    else:
        return jsonify({"error": "Authorization token is missing or invalid"}), 401
@app.route('/auth/login', methods=['GET'])
def auth_login():
    carid = request.args.get('carid')
    if carid == '11111cs':
        return jsonify({"error": "Invalid carid"}), 400

    # 获取cookie中的username和password
    username = request.cookies.get('username')
    password = request.cookies.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    # 连接数据库
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            # 根据username和password获取token
            sql = "SELECT `token` FROM `user` WHERE `username` = %s AND `password` = %s"
            cursor.execute(sql, (username, password))
            result = cursor.fetchone()

            if result:
                token = result['token']

                # 模拟登录逻辑
                login_url = f"http://23.224.111.139:8300/auth/login?carid={carid}"
                login_data = {'usertoken': token, 'action': 'default'}
                login_response = requests.post(login_url, data=login_data, allow_redirects=False)

                # 如果POST请求返回200，则返回特定错误消息
                if login_response.status_code == 200:
                    return jsonify({"error": "你非plus会员或会员已到期，请联系管理员"}), 403

                # 根据响应进行重定向或返回响应
                if login_response.status_code == 302:
                    response = make_response(redirect(login_response.headers['Location']))
                else:
                    response = make_response(login_response.text, login_response.status_code)

                # 复制所有从login_response中接收的cookies到最终响应中
                for key, value in login_response.cookies.items():
                    response.set_cookie(key, value)

                # 复制headers（可选）
                for key, value in login_response.headers.items():
                    if key.lower() not in ['content-length', 'content-encoding', 'transfer-encoding']:
                        response.headers[key] = value

                return response
            else:
                return jsonify({"error": "Invalid username or password"}), 401

    finally:
        connection.close()

@app.route('/list/list.html', methods=['GET'])
def list_html():
    # 获取cookie中的username和password
    username = request.cookies.get('username')
    password = request.cookies.get('password')

    if not username or not password:
        return "你未登录"

    # 连接数据库
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            # 查询username和password是否匹配
            sql = "SELECT 1 FROM `user` WHERE `username` = %s AND `password` = %s"
            cursor.execute(sql, (username, password))
            result = cursor.fetchone()

            if result:
                # 如果匹配，返回HTML内容
                html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <link rel="icon" href="/list/favicon.ico">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Chat GPT Online</title>
  <script type="module" crossorigin src="/list/assets/index-bVskRofl.js"></script>
  <link rel="stylesheet" crossorigin href="/list/assets/index-5wcFod3s.css">
  <style>
    #logout-btn, #activate-btn {
      padding: 5px 10px;
      background-color: #007bff;
      color: white;
      border: none;
      border-radius: 12px;
      cursor: pointer;
      font-size: 14px;
      display: flex;
      align-items: center;
      gap: 5px;
    }
    #logout-btn:hover, #activate-btn:hover {
      background-color: #0056b3;
    }
    #logout-btn {
      position: fixed;
      top: 10px;
      left: 10px;
    }
    #activate-btn {
      position: fixed;
      top: 50px;
      left: 10px;
    }
    #expiry-time {
      position: fixed;
      top: 10px;
      left: 50%;
      transform: translateX(-50%);
      font-size: 16px;
      color: white;
      background-color: rgba(0, 0, 0, 0.7);
      padding: 5px 10px;
      border-radius: 12px;
    }
    #activation-form {
      display: none;
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: white;
      border: 1px solid #ccc;
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
      text-align: center;
    }
    #activation-code {
      padding: 5px;
      font-size: 14px;
      border: 1px solid #ccc;
      border-radius: 12px;
      margin-bottom: 10px;
      width: calc(100% - 20px);
    }
    #submit-activation-btn {
      padding: 5px 10px;
      background-color: #28a745;
      color: white;
      border: none;
      border-radius: 12px;
      cursor: pointer;
      font-size: 14px;
      display: flex;
      align-items: center;
      gap: 5px;
    }
    #submit-activation-btn:hover {
      background-color: #218838;
    }
  </style>
</head>
<body>
  <div id="expiry-time">到期时间: 加载中...</div>
  <button id="logout-btn">注销登录</button>
  <button id="activate-btn">兑换</button>
  <div id="activation-form">
    <input type="text" id="activation-code" placeholder="输入激活码">
    <button id="submit-activation-btn"><img src="/path/to/submit-icon.svg" alt="Submit"> 提交</button>
  </div>
  <div id="app"></div>
  <script>
    document.getElementById('logout-btn').addEventListener('click', function() {
      window.location.href = '/list/login.html';
    });

    document.getElementById('activate-btn').addEventListener('click', function() {
      const activationCode = prompt('请输入激活码:');
      if (activationCode) {
        fetch('/activate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ code: activationCode })
        }).then(response => response.json()).then(data => {
          alert(data.success ? '激活成功，到期时间: ' + data.expiryTime : '激活失败: ' + data.error);
          if (data.success && data.expiryTime) {
            document.getElementById('expiry-time').textContent = '到期时间: ' + data.expiryTime;
            document.cookie = "usertoken=" + activationCode + "; path=/";
          }
        });
      } else {
        alert('请输入激活码');
      }
    });

    const usertoken = document.cookie.split('; ').find(row => row.startsWith('usertoken=')).split('=')[1];
    if (usertoken === 'cszy') {
      document.getElementById('expiry-time').textContent = '目前为测试免费3.5';
    } else {
      fetch('/expiretime')
        .then(response => response.json())
        .then(data => {
          const expireTime = new Date(data.expireTime).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });
          document.getElementById('expiry-time').textContent = '到期时间: ' + expireTime;
        });
    }
  </script>
</body>
</html>
                """
                return Response(html_content, mimetype='text/html')
            else:
                # 如果不匹配，返回未登录信息
                return "你未登录"
    finally:
        connection.close()

@app.route('/activate', methods=['POST'])
def activate():
    data = request.json
    code = data.get('code')

    if not code:
        return jsonify({"error": "激活码不能为空"}), 400

    # 连接数据库
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            # 获取 cookie 中的 username 和 password
            username = request.cookies.get('username')
            password = request.cookies.get('password')

            if not username or not password:
                return jsonify({"error": "用户未登录"}), 400

            # 查询用户的当前 token
            user_token_sql = "SELECT `token` FROM `user` WHERE `username` = %s AND `password` = %s"
            cursor.execute(user_token_sql, (username, password))
            user_token_result = cursor.fetchone()

            if not user_token_result:
                return jsonify({"error": "用户未登录"}), 400

            current_token = user_token_result['token']

            # 查询当前目录下 code.txt 文件的天数
            days_file_path = os.path.join(os.getcwd(), f"{code}.txt")
            if os.path.exists(days_file_path):
                with open(days_file_path, 'r') as file:
                    days = int(file.read().strip())
                os.remove(days_file_path)
            else:
                return jsonify({"error": "激活码无效或已到期"}), 400

            if current_token == 'cszy':
                if days > 0:
                    # 设置新的 token 的 expireTime 为现在时间加上天数
                    new_expire_time = datetime.now() + timedelta(days=days)

                    # 更新 chatgpt_user 表中新的 token 的 expireTime
                    update_expire_sql = "UPDATE `chatgpt_user` SET `expireTime` = %s WHERE `userToken` = %s"
                    cursor.execute(update_expire_sql, (new_expire_time, code))
                    connection.commit()

                    # 更新用户表中的 token
                    update_sql = "UPDATE `user` SET `token` = %s WHERE `username` = %s AND `password` = %s"
                    cursor.execute(update_sql, (code, username, password))
                    connection.commit()

                    # 创建响应对象并设置新的 usertoken cookie
                    expiry_time = new_expire_time.strftime('%Y-%m-%d %H:%M:%S')
                    response = jsonify({"success": True, "expiryTime": expiry_time, "message": f"激活成功，新的到期时间是: {expiry_time}"})
                    response.set_cookie('usertoken', code, path='/')

                    return response
            else:
                if days > 0:
                    # 查询当前 token 的 expireTime
                    expire_time_sql = "SELECT `expireTime` FROM `chatgpt_user` WHERE `userToken` = %s"
                    cursor.execute(expire_time_sql, (current_token,))
                    expire_time_result = cursor.fetchone()

                    if expire_time_result:
                        new_expire_time = expire_time_result['expireTime'] + timedelta(days=days)
                        # 更新 chatgpt_user 表中的 expireTime
                        update_expire_sql = "UPDATE `chatgpt_user` SET `expireTime` = %s WHERE `userToken` = %s"
                        cursor.execute(update_expire_sql, (new_expire_time, current_token))
                        connection.commit()

                        return jsonify({"success": True, "expiryTime": new_expire_time.strftime('%Y-%m-%d %H:%M:%S'), "message": f"激活成功，新的到期时间是: {new_expire_time.strftime('%Y-%m-%d %H:%M:%S')}"})

            # 查询激活码是否有效
            sql = "SELECT `expireTime`, `isPlus` FROM `chatgpt_user` WHERE `userToken` = %s"
            cursor.execute(sql, (code,))
            result = cursor.fetchone()

            if not result or result['expireTime'] < datetime.now():
                return jsonify({"error": "激活码无效或已到期"}), 400

            # 更新用户表中的 token
            update_sql = "UPDATE `user` SET `token` = %s WHERE `username` = %s AND `password` = %s"
            cursor.execute(update_sql, (code, username, password))
            connection.commit()

            # 创建响应对象并设置新的 usertoken cookie
            expiry_time = result['expireTime'].strftime('%Y-%m-%d %H:%M:%S')
            response = jsonify({"success": True, "expiryTime": expiry_time, "message": f"激活成功，新的到期时间是: {expiry_time}"})
            response.set_cookie('usertoken', code, path='/')

            return response
    finally:
        connection.close()
@app.route('/list.js', methods=['GET'])
def serve_list_js():
    js_code = """
$(function () {
  var alertShown = false; // Flag to ensure the alert is shown only once
  var monitorInterval; // To hold the reference to setInterval

  var $div = $("<div></div>");
  $div.css({
    "border-radius": "10px",
    background: "#000000",
    color: "#FFFFFF",
    height: "30px",
    width: "50px",
    display: "flex",
    "align-items": "center",
    "justify-content": "center",
    position: "fixed",
    right: "5px",
    top: "50px",
    cursor: "pointer",
    "box-shadow": "0 2px 5px rgba(0, 0, 0, 0.2)",
  });
  $div.html("<span style='color:white;font-size:16px;'>更多</span>");
  $("body").append($div);

  var $dropdownMenu = $("<div></div>");
  $dropdownMenu.css({
    display: "none",
    position: "fixed",
    right: "5px",
    top: "80px",
    background: "#fff",
    border: "1px solid #ccc",
    "border-radius": "3px",
    "box-shadow": "0 2px 5px rgba(0, 0, 0, 0.2)",
    "z-index": "999",
  });

  var $expireLabel = $("<div style='padding: 10px; color: black; font-size: 16px;'></div>");
  $dropdownMenu.append($expireLabel);

  var options = [
    { label: "🔁切换4.0账号", action: "switchLine" },
  ];

  function refreshMenuOptions(isPermanent) {
    $dropdownMenu.empty();
    $dropdownMenu.append($expireLabel);
    options.forEach(function (option) {
      var $option = $("<div style='padding: 10px; cursor: pointer;'></div>");
      $option.text(option.label);
      $option.click(function () {
        if (option.target === "_blank") {
          window.open(option.url, "_blank");
        } else if (option.action === "switchLine") {
          var usertoken = getCookie("usertoken");
          if (usertoken) {
            window.location.href = `/list/list.html`;
          } else {
            alert("未找到usertoken，请先登录。");
          }
        } else {
          window.location.href = option.url;
        }
      });
      $dropdownMenu.append($option);
    });
  }

  $("body").append($dropdownMenu);

  $div.click(function () {
    $dropdownMenu.toggle();
    fetchExpiryDate(); // 当用户点击菜单时更新到期时间
  });

  $(document).click(function (event) {
    if (!$(event.target).closest($div).length && !$(event.target).closest($dropdownMenu).length) {
      $dropdownMenu.hide();
    }
  });

  function getCookie(name) {
    var value = "; " + document.cookie;
    var parts = value.split("; " + name + "=");
    if (parts.length === 2) {
      return parts.pop().split(";").shift();
    }
  }

  function fetchExpiryDate() {
    $.ajax({
      url: "/expiretime",
      success: function(data) {
        var expireDate = new Date(data.expireTime);
        var now = new Date();
        var tenYearsLater = new Date(now.setFullYear(now.getFullYear() + 10));
        if (expireDate > tenYearsLater) {
          $expireLabel.text("到期时间: 永久有效");
          refreshMenuOptions(true);
        } else {
          var date = expireDate.toLocaleString('zh-CN', { hour12: false });
          $expireLabel.text("到期时间: " + date);
          refreshMenuOptions(false);
        }
      },
      error: function(xhr) {
        if (xhr.status === 401) {
          if (!alertShown) {
            alert("检测到异地登录，您将被重定向到首页。");
            alertShown = true;
            clearInterval(monitorInterval); // Stop monitoring
          }
          window.location.href = "/list"; // Redirect to the homepage
        }
      }
    });
  }

  fetchExpiryDate(); // 初始加载时获取到期时间

  monitorInterval = setInterval(fetchExpiryDate, 5000); // Set up the monitoring
});
    """
    return Response(js_code, mimetype='application/javascript')
@app.route('/reg', methods=['GET'])
def register():
    # Retrieve username and password from the request
    username = request.args.get('username', None)
    password = request.args.get('password', None)
    token = request.args.get('token', 'cszy')
    if token == "":
        token = "cszy"  # Default token is "cszy"

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    # Connect to the database
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            # Check if the username already exists
            username_check_sql = "SELECT 1 FROM `user` WHERE `username` = %s"
            cursor.execute(username_check_sql, (username,))
            if cursor.fetchone():
                return jsonify({"error": "Username already exists"}), 409

            if token != 'cszy':  # If token is provided and is not the default
                # Query to check the token's validity and expiration
                token_check_sql = "SELECT `expireTime` FROM `chatgpt_user` WHERE `userToken` = %s"
                cursor.execute(token_check_sql, (token,))
                result = cursor.fetchone()

                if not result:
                    return jsonify({"error": "Token not found or invalid"}), 404

                # Check if the token has expired
                if result['expireTime'] < datetime.now():
                    return jsonify({"error": "Token has expired"}), 403

                # Check if the token has already been bound to a user
                token_bound_check_sql = "SELECT 1 FROM `user` WHERE `token` = %s"
                cursor.execute(token_bound_check_sql, (token,))
                if cursor.fetchone():
                    return jsonify({"error": "Token has already been used"}), 409

                # 查询当前目录下 code.txt 文件的天数
                days_file_path = os.path.join(os.getcwd(), f"{token}.txt")
                if os.path.exists(days_file_path):
                    with open(days_file_path, 'r') as file:
                        days = int(file.read().strip())
                    os.remove(days_file_path)  # 删除 code.txt 文件
                else:
                    return jsonify({"error": "激活码无效或已到期"}), 400

                # 设置新的 token 的 expireTime 为现在时间加上天数
                new_expire_time = datetime.now() + timedelta(days=days)

                # 更新 chatgpt_user 表中新的 token 的 expireTime
                update_expire_sql = "UPDATE `chatgpt_user` SET `expireTime` = %s WHERE `userToken` = %s"
                cursor.execute(update_expire_sql, (new_expire_time, token))
                connection.commit()

            # Insert the new user data into the user table
            insert_sql = "INSERT INTO `user` (username, password, token) VALUES (%s, %s, %s)"
            cursor.execute(insert_sql, (username, password, token))
            connection.commit()

            # If the insertion is successful, return a success response
            return jsonify({"isSuccess": "1"})
    finally:
        connection.close()

@app.route('/xinlogin', methods=['POST'])
def login1():
    # 获取请求中的JSON数据
    data = request.get_json()
    # Get username and password from the JSON body of the request
    username = request.form.get('username')
    password = request.form.get('password')
    action = request.form.get('action')

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    # 连接到数据库
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            # 查询用户名和密码是否匹配
            sql = "SELECT `token` FROM `user` WHERE `username` = %s AND `password` = %s"
            cursor.execute(sql, (username, password))
            result = cursor.fetchone()

            if result:
                # 如果用户存在，获取token
                token = result['token']
                
                # 设置cookie
                response = make_response(redirect('/list/list.html'))
                response.set_cookie('username', username)
                response.set_cookie('password', password)
                response.set_cookie('usertoken', token)
                return response

            else:
                # 如果用户不存在或密码不正确
                return jsonify({"error": "Account or password is incorrect"}), 401

    finally:
        connection.close()
        
@app.route('/users', methods=['GET'])
def list_users():
    # 连接到数据库
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            # 查询所有用户
            sql = "SELECT username FROM user"
            cursor.execute(sql)
            users = cursor.fetchall()
            # 转换查询结果为列表形式
            user_list = [user['username'] for user in users]
            return jsonify(user_list)
    finally:
        connection.close()
    
    
@app.route('/login', methods=['GET'])
def login():
    # 从请求中获取token
    token = request.args.get('token', None)
    if not token:
        return jsonify({"error": "Token is required"}), 400

    # 连接数据库
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            # 查找用户的expireTime和isPlus
            sql = "SELECT `expireTime`, `isPlus` FROM `chatgpt_user` WHERE `userToken` = %s"
            cursor.execute(sql, (token,))
            result = cursor.fetchone()

            if not result:
                return jsonify({"error": "Token not found"}), 404

            # 检查expireTime是否过期
            if result['expireTime'] < datetime.now():
                return jsonify({"error": "Token has expired"}), 403

            # 如果是Plus会员
            if result['isPlus']:
                response_url = 'http://改成自己的/plus.php'
            else:
                # 如果不是Plus会员
                response_url = 'http://改成自己的/free.php'

            # 请求获取名称
            name_response = requests.get(response_url)
            if name_response.status_code == 200:
                carid = name_response.text.strip()
                
                # 模拟登录POST请求
                login_url = f"http://23.224.111.139:8300/auth/login?carid={carid}"
                login_data = {'usertoken': token, 'action': 'default'}
                login_response = requests.post(login_url, data=login_data, allow_redirects=False)
                
                # 根据响应进行重定向或返回响应
                if login_response.status_code == 302:
                    response = make_response(redirect(login_response.headers['Location']))
                else:
                    response = make_response(login_response.text, login_response.status_code)

                # 复制所有从login_response中接收的cookies到最终响应中
                for key, value in login_response.cookies.items():
                    response.set_cookie(key, value)

                # 复制headers（可选）
                for key, value in login_response.headers.items():
                    if key.lower() not in ['content-length', 'content-encoding', 'transfer-encoding']:
                        response.headers[key] = value

                return response

            else:
                return jsonify({"error": "Failed to retrieve carID"}), 500

    finally:
        connection.close()

@app.route('/xufei', methods=['GET'])
def renew_subscription():
    token = request.args.get('token', '')

    # Connect to the database to fetch isPlus status
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            # SQL query to fetch the isPlus for the given token
            sql = "SELECT `isPlus` FROM `chatgpt_user` WHERE `userToken` = %s"
            cursor.execute(sql, (token,))
            result = cursor.fetchone()
            if result is None:
                return jsonify({'error': 'Token not found'}), 404
            
            # Set commodity_id based on isPlus status
            commodity_id = 117 if result['isPlus'] == 0 else 116
    finally:
        connection.close()

    # Prepare data for the POST request with dynamic commodity_id
    post_data = {
        "contact": "819220120@qq.com",
        "password": "Tuo2293389",
        "coupon": "",
        "num": 1,
        "token": token,
        "commodity_id": commodity_id,
        "card_id": 0,
        "pay_id": 5,
        "device": 0,
        "from": 0,
        "race": ""
    }

    # URL for the POST request
    post_url = "https://vip.ilovechatgpt.top/user/api/order/trade"

    # Send the POST request
    response = requests.post(post_url, data=post_data)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        response_data = response.json()
        if response_data.get('code') == 200:
            # Redirect to the payment URL
            redirect_url = f"https://vip.ilovechatgpt.top/{response_data['data']['url']}"
            return redirect(redirect_url)
        else:
            # Handle cases where the API returned an error
            return jsonify({"error": "Failed to process order", "message": response_data.get('msg')}), 400
    else:
        # If the POST request failed
        return jsonify({"error": "Failed to communicate with the order API"}), 500
@app.route('/expiretime', methods=['GET'])
def query_ex1pire_time():
    # Retrieve userToken from user's cookies
    user_token = request.cookies.get('usertoken')
    
    # Handle case where usertoken is not present in the cookies
    if not user_token:
        return jsonify({'error': 'User token not found'}), 400

    # Connect to the database
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            # SQL query to fetch the expireTime for the given userToken
            sql = "SELECT `expireTime` FROM `chatgpt_user` WHERE `userToken` = %s"
            cursor.execute(sql, (user_token,))
            result = cursor.fetchone()
            if result:
                return jsonify({'expireTime': result['expireTime']})
            else:
                return jsonify({'error': 'No record found'}), 404
    finally:
        connection.close()
@app.route('/backend-api/user_surveys/active', methods=['GET', 'POST'])
def proxy_request():
    # 获取请求的目标 URL
    target_url = 'http://23.224.111.139:8300/backend-api/user_surveys/active'
    
    # 提取请求方法和头部
    method = request.method
    headers = dict(request.headers)
    
    # 提取 Authorization 信息
    auth_header = headers.get('Authorization')
    
    # 准备转发的 headers，去掉 host 因为目标服务器可能有不同的 host 配置
    headers.pop('Host', None)
    
    if auth_header and auth_header.startswith('Bearer '):
        # 从 Authorization 中提取 token
        token = auth_header.split(' ')[1]
        
        # 发送请求到目标服务器
        if method == 'GET':
            resp = requests.get(target_url, headers=headers)
        elif method == 'POST':
            resp = requests.post(target_url, headers=headers, data=request.data)
        
        # 使用 chardet 自动检测编码
        detected_encoding = chardet.detect(resp.content)['encoding']
        
        # 解码响应内容
        content = resp.content.decode(detected_encoding)
        
        # 创建响应对象
        response = make_response(content, resp.status_code)
        
        # 设置所有从原始响应中获取的 headers
        for name, value in resp.headers.items():
            if name.lower() not in ['content-length', 'content-encoding', 'transfer-encoding']:
                response.headers[name] = value
        
        # 添加 usertoken cookie
        response.set_cookie('usertoken', token)
        
        # 返回响应
        return response
    else:
        return "Authorization token is missing or invalid", 401
def query_expire_time(user_token):
    # 连接数据库
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            # 查询到期时间
            sql = "SELECT `expireTime` FROM `chatgpt_user` WHERE `userToken`=%s"
            cursor.execute(sql, (user_token,))
            result = cursor.fetchone()
            return result['expireTime'] if result else None
    finally:
        connection.close()
def filte2r_gizmos_by_user():
    method = request.method
    data = request.get_data()
    cookies = request.cookies
    headers = {key: value for key, value in request.headers if key != 'Host'}
    user_token = request.headers.get('Authorization').split(' ')[1]  # 获取 Bearer token
    USER_ID_FILE_PATH = user_token + ".txt"

    # 读取用户 ID，处理可能存在的多个 ID
    with open(USER_ID_FILE_PATH, 'r') as file:
        user_ids = file.read().strip().split()
    
    # 发送请求获取数据
    target_url = "http://23.224.111.139:8300/public-api/gizmos/discovery/mine"
    resp = requests.request(method, target_url, headers=headers, data=data, allow_redirects=False, cookies=cookies)

    if resp.status_code == 200:
        data = resp.json()
        gizmos = data.get('gizmos', [])
        
        # 过滤出用户ID对应的部分，考虑文件中可能有多个 ID
        filtered_gizmos = [gizmo for gizmo in gizmos if gizmo['resource']['gizmo']['id'] in user_ids]
        
        # 重新构造返回的 JSON 数据，保留原始结构中其他部分的内容不变
        result_data = data  # 复制原始数据
        result_data['gizmos'] = filtered_gizmos  # 替换 gizmos 部分为筛选后的数据

        return jsonify(result_data)

    return jsonify({"error": "Failed to fetch data"}), 500
@app.route('/backend-api/gizmos/<variable>/<path:subpath>', methods=['POST', 'DELETE'])
def modify_file(variable, subpath):
    # 获取请求头中的Authorization，并提取Bearer token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authorization token is missing or invalid"}), 401
    
    user_token = auth_header.split(' ')[1]
    USER_ID_FILE_PATH = user_token + ".txt"
    
    data = request.json  # 获取 JSON 数据
    action = data.get('action')

    # 确保文件存在，如果不存在则创建
    if not os.path.exists(USER_ID_FILE_PATH):
        open(USER_ID_FILE_PATH, 'a').close()
    if request.method == 'DELETE':
        if os.path.exists(USER_ID_FILE_PATH):
            with open(USER_ID_FILE_PATH, 'r') as file:
                lines = file.readlines()
            with open(USER_ID_FILE_PATH, 'w') as file:
                for line in lines:
                    if line.strip() != variable:  # 保留不是指定内容的行
                        file.write(line)
        return Response('null', status=200, mimetype='application/json')

    if action == 'keep':
        # 将变量 "xxx" 和动态路径部分 "sidebar" 添加到 user_token.txt 文件中
        content_to_add = "\n" + variable
        with open(USER_ID_FILE_PATH, 'a') as file:
            file.write(content_to_add)
        return Response('null', status=200, mimetype='application/json')
    
    elif action == 'hide':
        # 从 user_token.txt 文件中删除变量 "xxx" 和路径 "sidebar"
        try:
            with open(USER_ID_FILE_PATH, 'r') as file:
                lines = file.readlines()
            with open(USER_ID_FILE_PATH, 'w') as file:
                content_to_remove = variable
                for line in lines:
                    if line.strip() != content_to_remove:  # 保留不是指定内容的行
                        file.write(line)
            return Response('null', status=200, mimetype='application/json')
        except FileNotFoundError:
            return jsonify({"error": "User token file not found"}), 404
    else:
        # 对于非 "keep" 和 "hide" 操作，检查 subpath 是否等于 promote
        if subpath == 'promote':
            # 构建文件路径
            file_path = f'mine{user_token}.txt'
            
            # 如果文件不存在，则创建文件
            if not os.path.exists(file_path):
                open(file_path, 'a').close()
            
            # 将 variable 写入文件，确保每行存储一个 variable
            with open(file_path, 'a') as file:
                file.write(f'{variable}\n')
        
        # 转发请求到 proxy 函数
        return proxy(f'backend-api/gizmos/{variable}/{subpath}')
def duihua(convid):
    # 从数据库获取 email 和 chatgptaccountid
    result = query_email_and_accountid(convid)
    if result:
        email, chatgptaccountid = result['email'], result.get('chatgptaccountid')
        # 通过 email 获取 carID
        carid_result = query_carid(email)
        if carid_result:
            carid = carid_result['carID']
            user_token = request.headers.get('Authorization')
        if user_token:
            user_token = user_token.replace("Bearer ", "")
            global_conversations = query_conversations(user_token)
            # 使用用户的 cookie 模拟登录
            simulate_login(carid, request.cookies, user_token)

            # 在此处修改 cookie，添加 _account=chatgptaccountid
            modified_cookies = request.cookies.copy()
            if chatgptaccountid:
                modified_cookies['_account'] = chatgptaccountid
            else:
                modified_cookies['_account'] = ""
            # 准备转发请求

            target_url = "http://23.224.111.139:8300/backend-api/conversation"
            method = request.method
            data = request.get_data()
            headers = {key: value for key, value in request.headers if key != 'Host'}
            
            # 如果 chatgptaccountid 存在，修改请求头
            if chatgptaccountid:
                headers['Chatgpt-Account-Id'] = chatgptaccountid
                headers['ChatGPT-Account-ID'] = chatgptaccountid
            else:
                # 如果 chatgptaccountid 不存在，确保不包含该请求头
                headers.pop('Chatgpt-Account-Id', None)
                headers.pop('ChatGPT-Account-ID', None)

            # 为转发的请求准备 cookie
            cookies = '; '.join([f"{key}={value}" for key, value in modified_cookies.items()])
            headers['Cookie'] = cookies
            headers['Accept-Encoding'] = 'gzip, deflate'
            
            # 发送请求，启用流式传输
            resp = requests.request(method, target_url, headers=headers, data=data, cookies=modified_cookies, stream=True)
            
            # 创建一个生成器，边读边转发响应体
            def generate():
                for chunk in resp.iter_content(chunk_size=4096):
                    yield chunk

            # 过滤掉不需要的头部信息
            excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
            headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]

            # 返回流式响应
            return Response(generate(), status=resp.status_code, headers=headers)

def cnmbgpt(convid):
    
    # 从数据库获取 email 和 chatgptaccountid
    result = query_email_and_accountid(convid)
    if result:
        email, chatgptaccountid = result['email'], result.get('chatgptaccountid')
        # 通过 email 获取 carID
        carid_result = query_carid(email)
        if carid_result:
            carid = carid_result['carID']
            user_token = request.headers.get('Authorization')
        if user_token:
            user_token = user_token.replace("Bearer ", "")
            global_conversations = query_conversations(user_token)
            # 使用用户的 cookie 模拟登录
            simulate_login(carid, request.cookies, user_token)

            # 在此处修改 cookie，添加 _account=chatgptaccountid
            modified_cookies = request.cookies.copy()
            if chatgptaccountid:
                modified_cookies['_account'] = chatgptaccountid
            else:
                modified_cookies['_account'] = ""
            # 准备转发请求
            target_url = "http://23.224.111.139:8300/backend-api/gizmos/pinned"
            method = request.method
            data = request.get_data()
            headers = {key: value for key, value in request.headers if key != 'Host'}
            
            # 如果 chatgptaccountid 存在，修改请求头
            if chatgptaccountid:
                
                headers['Chatgpt-Account-Id'] = chatgptaccountid
                headers['ChatGPT-Account-ID'] = chatgptaccountid
            else:
                # 如果 chatgptaccountid 不存在，确保不包含该请求头
                
                headers.pop('Chatgpt-Account-Id', None)
                headers.pop('ChatGPT-Account-ID', None)

            # 为转发的请求准备 cookie
            cookies = '; '.join([f"{key}={value}" for key, value in modified_cookies.items()])
            headers['Cookie'] = cookies
            headers['Accept-Encoding'] = 'gzip, deflate'
            resp = requests.request(method, target_url, headers=headers, data=data, cookies=modified_cookies)
            resp.encoding = 'utf-8'
            
            raw_data = resp.content
            decoded_data = raw_data.decode('utf-8')

            response = Response(decoded_data, resp.status_code, headers)
            

            excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
            headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]

            response = Response(decoded_data, resp.status_code, headers)
            return response
def shabigpt(convid):
    
    # 从数据库获取 email 和 chatgptaccountid
    result = query_email_and_accountid(convid)
    if result:
        email, chatgptaccountid = result['email'], result.get('chatgptaccountid')
        # 通过 email 获取 carID
        carid_result = query_carid(email)
        if carid_result:
            carid = carid_result['carID']
            user_token = request.headers.get('Authorization')
        if user_token:
            user_token = user_token.replace("Bearer ", "")
            global_conversations = query_conversations(user_token)
            # 使用用户的 cookie 模拟登录
            simulate_login(carid, request.cookies, user_token)

            # 在此处修改 cookie，添加 _account=chatgptaccountid
            modified_cookies = request.cookies.copy()
            if chatgptaccountid:
                modified_cookies['_account'] = chatgptaccountid
            else:
                modified_cookies['_account'] = ""
            # 准备转发请求
            target_url = "http://23.224.111.139:8300/backend-api/register-websocket"
            method = request.method
            data = request.get_data()
            headers = {key: value for key, value in request.headers if key != 'Host'}
            
            # 如果 chatgptaccountid 存在，修改请求头
            if chatgptaccountid:
                
                headers['Chatgpt-Account-Id'] = chatgptaccountid
                headers['ChatGPT-Account-ID'] = chatgptaccountid
            else:
                # 如果 chatgptaccountid 不存在，确保不包含该请求头
                
                headers.pop('Chatgpt-Account-Id', None)
                headers.pop('ChatGPT-Account-ID', None)

            # 为转发的请求准备 cookie
            cookies = '; '.join([f"{key}={value}" for key, value in modified_cookies.items()])
            headers['Cookie'] = cookies
            headers['Accept-Encoding'] = 'gzip, deflate'
            resp = requests.request(method, target_url, headers=headers, data=data, cookies=modified_cookies)
            resp.encoding = 'utf-8'
            
            raw_data = resp.content
            decoded_data = raw_data.decode('utf-8')

            response = Response(decoded_data, resp.status_code, headers)
            

            excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
            headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]

            response = Response(decoded_data, resp.status_code, headers)
            return response
def query_email_and_accountid(convid):
    # 连接数据库
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            # 获取 email 和 chatgptaccountid
            sql = "SELECT `email`, `chatgptaccountid` FROM `chatgpt_conversations` WHERE `convid`=%s"
            cursor.execute(sql, (convid,))
            result = cursor.fetchone()
            return result
    finally:
        connection.close()

def query_carid(email):
    # 连接数据库
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            # 获取 carID
            sql = "SELECT `carID` FROM `chatgpt_session` WHERE `email`=%s"
            cursor.execute(sql, (email,))
            result = cursor.fetchone()
            return result
    finally:
        connection.close()

def simulate_login(carid, cookies, usertoken):
    # 模拟登录
    url = f"{AUTH_TARGET_URL}/auth/login?carid={carid}"
    # 添加 POST 请求的数据
    data = {
        'carid': carid,
        'usertoken': usertoken,  # 假设这里你已经有了usertoken的值
        'action': 'default'
    }
    requests.post(url, cookies=cookies, data=data)

@app.route('/backend-api/conversation/<convid>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def handle_conversation_request(convid):
    # 从数据库获取 email 和 chatgptaccountid
    result = query_email_and_accountid(convid)
    if result:
        email, chatgptaccountid = result['email'], result.get('chatgptaccountid')
        # 通过 email 获取 carID
        carid_result = query_carid(email)
        if carid_result:
            carid = carid_result['carID']
            user_token = request.headers.get('Authorization')
        if user_token:
            user_token = user_token.replace("Bearer ", "")
            global_conversations = query_conversations(user_token)
            # 使用用户的 cookie 模拟登录
            
            simulate_login(carid, request.cookies,user_token)

            # 准备转发请求
            target_url = f"{TARGET_URL}/backend-api/conversation/{convid}"
            print ("666")
            if request.method == 'POST':
               json_data = request.json
               if "title" in json_data:
                  title = json_data["title"]
                  return update_conversation_title(convid,title)
            
            method = request.method
            data = request.get_data()
            headers = {key: value for key, value in request.headers if key != 'Host'}
            modified_cookies = request.cookies.copy()
            # 如果 chatgptaccountid 存在，修改请求头
            
            if chatgptaccountid:
                headers['Chatgpt-Account-Id'] = chatgptaccountid
                headers['ChatGPT-Account-ID'] = chatgptaccountid
                modified_cookies['_account'] = chatgptaccountid
            else:
                
                # 如果 chatgptaccountid 不存在，确保不包含该请求头
                headers.pop('Chatgpt-Account-Id', None)
                headers.pop('ChatGPT-Account-ID', None)
                modified_cookies['_account'] = ""
                
            headers['Accept-Encoding'] = 'gzip, deflate'
            if request.method == 'PATCH' and request.json == {"is_archived": False}:
                return huifudange_conversations(convid)
            if request.method == 'PATCH' and request.json == {"is_visible": False}:
                return shanchudange_conversations(convid)
            if request.method == 'PATCH' and request.json == {"is_archived": True}:
                return guidangdange_conversations(convid)
            else:
                method = request.method
            resp = requests.request(method, target_url, headers=headers, data=data, allow_redirects=False,cookies=modified_cookies)
            resp.encoding = 'utf-8'
            raw_data = resp.content
            decoded_data = raw_data.decode('utf-8')
            excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
            headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
            
            encoded_carid = quote(carid, safe='') 
            new_cookie_value = f"zhanghao={encoded_carid}; Path=/;"
            headers.append(('Set-Cookie', new_cookie_value))
            new_headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
            new_headers.append(('Set-Cookie', new_cookie_value))
            if request.method == 'GET':
                decoded_data=update_json_title_with_db_title(decoded_data,convid)
                
                
            response = Response(decoded_data, resp.status_code,new_headers)
            
            return response
    return jsonify({"error": "Invalid convid or email not found"}), 400



@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def proxy(path):
    if path == "backend-api/conversations" and request.args.get('offset') == '0' and request.args.get('limit') == '28' and request.args.get('order') == 'updated':
        user_token = request.headers.get('Authorization')
        if user_token:
            user_token = user_token.replace("Bearer ", "")
            global_conversations = query_conversations(user_token)
            formatted_conversations = [{
                'id': conv['convid'],
                'title': conv['title'],
                'create_time': conv['createTime'],
                'update_time': conv['updateTime']
            } for conv in global_conversations]
            return jsonify({
                "has_missing_conversations": False,
                "items": formatted_conversations,
                "limit": 28,
                "offset": 0,
                "total": len(formatted_conversations)
            })
    if path == "backend-api/conversations" and request.args.get('limit') == '30' and request.args.get('order') == 'updated'and request.args.get('is_archived') == 'true':
        user_token = request.headers.get('Authorization')
        if user_token:
            user_token = user_token.replace("Bearer ", "")
            global_conversations = guidang(user_token)
            formatted_conversations = [{
                'id': conv['convid'],
                'title': conv['title'],
                'create_time': conv['createTime'],
                'update_time': conv['updateTime']
            } for conv in global_conversations]
            return jsonify({
                "has_missing_conversations": False,
                "items": formatted_conversations,
                "limit": 28,
                "offset": 0,
                "total": len(formatted_conversations)
            })

    a=1    

    if request.query_string:
        if path.startswith("backend-api/conversation"):
        # 然后，使用更加具体的条件检查路径是否以斜线结尾
               if path.endswith("/"):
            # 特殊处理对话请求request，提取对话ID
                 convid = path.split('/')[-2]  # 因为路径以斜线结尾，所以倒数第二个元素是ID
                 return handle_conversation_request(convid)
               if request.method == 'POST':
        # 解析JSON请求体
                  data = request.json
        # 提取conversation_id
                  convid = data.get('conversation_id')
                  if convid:
                    return duihua(convid)
        target_url = f"{TARGET_URL}/{path}?{request.query_string.decode('utf-8')}"
    else:
        if path.startswith("backend-api/conversation"):
        # 然后，使用更加具体的条件检查路径是否以斜线结尾
               if path.endswith("/"):
            # 特殊处理对话请求request，提取对话ID
                 convid = path.split('/')[-2]  # 因为路径以斜线结尾，所以倒数第二个元素是ID
                 return handle_conversation_request(convid)
               if request.method == 'POST':
        # 解析JSON请求体
                  data = request.json
        # 提取conversation_id
                  convid = data.get('conversation_id')
                  if convid:
                    return duihua(convid)
        target_url = f"{TARGET_URL}/{path}"
    css=None
    method = request.method
    data = request.get_data()
    headers = {key: value for key, value in request.headers if key != 'Host'}
    headers['Accept-Encoding'] = 'gzip, deflate'
    referer = headers.get('Referer', '默认值')
    if referer!='':
        extracted_id = None
        modified_cookies = request.cookies.copy()
    if path.startswith("backend-api/conversation/gen_title/"):
        css='true'
    if path.startswith("c/"):
        css='true'
    if 'c/' in referer and css!='true':
        extracted_id = referer.split('c/')[1].split('/')[0]
        if extracted_id:
            result = query_email_and_accountid(extracted_id)
            if result:
              chatgptaccountid = result.get('chatgptaccountid', '')
            

              if chatgptaccountid:
                  modified_cookies['_account'] = chatgptaccountid
                  headers['Chatgpt-Account-Id'] = chatgptaccountid
                  headers['ChatGPT-Account-ID'] = chatgptaccountid
               
                
              else:
                
                  modified_cookies['_account'] = ""
                  headers.pop('Chatgpt-Account-Id', None)
                  headers.pop('ChatGPT-Account-ID', None)

                
                
                
            
    if path.startswith("backend-api/register-websocket"):

        if extracted_id:
            return shabigpt(extracted_id)
            
               
    if  path.startswith("backend-api/conversations")and request.json.get("is_visible") is False:
        print("shanchu")
        user_token = request.headers.get('Authorization')
        if user_token:
            user_token = user_token.replace("Bearer ", "")
            print ("SHANCHU")
        return shanchu_conversations(user_token) 
    json_data = request.json
    if path == "backend-api/conversations"and request.json.get("is_archived") is True:
        user_token = request.headers.get('Authorization')
        
        
        if user_token:
            user_token = user_token.replace("Bearer ", "")
        return guidang_conversations(user_token)
    pattern = r'^backend-api/aip/p/[^/]+/user-settings$'
    if re.match(pattern, path):
        method='PATCH'
        print (method)
    if 'Accept' in headers and headers['Accept'] == 'text/event-stream':
    # 启用流式输出
      print ('cnmgpt')
      resp = requests.request(method, target_url, headers=headers, data=data, cookies=modified_cookies, stream=True)
    
    # 创建一个生成器，边读边转发响应体
      def generate():
          for chunk in resp.iter_content(chunk_size=4096):
              yield chunk

    # 过滤掉不需要的头部信息
      excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
      headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]

    # 返回流式响应
      return Response(generate(), status=resp.status_code, headers=headers)
    else:
    # 不使用流式输出
      resp = requests.request(method, target_url, headers=headers, data=data, allow_redirects=False, cookies=modified_cookies)
    resp.encoding = 'utf-8'
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
    user_token = request.cookies.get('usertoken')
    if user_token:
        expire_time = query_expire_time(user_token)
    else:
        expire_time = "未登录"

    # JavaScript代码注入
    js_code = f"""
     <script>
     
    </script>
    """
    if 'text/html' in resp.headers.get('Content-Type', ''):
        content = resp.text.replace('</body>', js_code + '</body>')  # 在</body>标签前插入JS代码
        response = Response(content, resp.status_code, headers)
    else:
        response = Response(resp.content, resp.status_code, headers)

    return response
def query_conversations(user_token):
    # 连接数据库
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
        
            sql = """
            SELECT `convid`, `title`, `createTime`, `updateTime`, `chatgptaccountid`
            FROM `chatgpt_conversations`
            WHERE `usertoken` = %s AND `deleted_at` IS NULL
            ORDER BY `updateTime` DESC
            """
            cursor.execute(sql, (user_token,))
            results = cursor.fetchall()
            # 确保时间格式化
            for result in results:
                result['createTime'] = result['createTime'].strftime('%Y-%m-%d %H:%M:%S')
                result['updateTime'] = result['updateTime'].strftime('%Y-%m-%d %H:%M:%S')
            return results
    finally:
        connection.close()
def guidang(user_token):
    # 连接数据库
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
        
            sql = """
                 SELECT `convid`, `title`, `createTime`, `updateTime`, `chatgptaccountid`
                 FROM `chatgpt_conversations`
                 WHERE `usertoken` = %s AND `deleted_at` IS NOT NULL
                 ORDER BY `updateTime` DESC
            """
            cursor.execute(sql, (user_token,))
            results = cursor.fetchall()
            # 确保时间格式化
            for result in results:
                result['createTime'] = result['createTime'].strftime('%Y-%m-%d %H:%M:%S')
                result['updateTime'] = result['updateTime'].strftime('%Y-%m-%d %H:%M:%S')
            return results
    finally:
        connection.close()
def shanchu_conversations(user_token):
    # 连接数据库
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            # 删除指定用户的会话记录
            sql = """
                 DELETE FROM `chatgpt_conversations`
                 WHERE `usertoken` = %s AND `deleted_at` IS  NULL;;
            """
            cursor.execute(sql, (user_token,))
            # 提交事务以确保数据被删除
            connection.commit()
            # 由于是删除操作，不需要返回任何查询结果
    finally:
        connection.close()

    # 返回一个表示操作成功的 JSON 对象
    return json.dumps({
        "message": None,
        "success": True
    })
def shanchudange_conversations(convid):
    # 连接数据库
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            # 删除指定用户的会话记录
            sql = """
               DELETE FROM `chatgpt_conversations`
               WHERE `convid` = %s;
            """
            cursor.execute(sql, (convid,))
            # 提交事务以确保数据被删除
            connection.commit()
            # 由于是删除操作，不需要返回任何查询结果
    finally:
        connection.close()

    # 返回一个表示操作成功的 JSON 对象
    return json.dumps({
        "message": None,
        "success": True
    })
def huifudange_conversations(convid):
    # 连接数据库
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            # 将指定用户的会话记录的 deleted_at 字段设置为 NULL
            sql = """
               UPDATE `chatgpt_conversations`
               SET `deleted_at` = NULL
               WHERE `convid` = %s;
            """
            cursor.execute(sql, (convid,))
            # 提交事务以确保更改被保存
            connection.commit()
            # 由于是更新操作，不需要返回任何查询结果
    finally:
        connection.close()

    # 返回一个表示操作成功的 JSON 对象
    return json.dumps({
        "message": "Conversation restored successfully.",
        "success": True
    })
def guidangdange_conversations(convid):
    # 连接数据库
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            # 将指定用户的会话记录的 deleted_at 字段设置为 NULL
            sql = """
               UPDATE `chatgpt_conversations`
               SET `deleted_at` = NULL
               WHERE `convid` = %s;
            """
            cursor.execute(sql, (convid,))
            # 提交事务以确保更改被保存
            connection.commit()
            # 由于是更新操作，不需要返回任何查询结果
    finally:
        connection.close()

    # 返回一个表示操作成功的 JSON 对象
    return json.dumps({
        "message": "Conversation restored successfully.",
        "success": True
    })
def guidangdange_conversations(convid):
    # Connect to the database
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            # Set the 'deleted_at' field to the current timestamp for the specified user's conversation record
            sql = """
               UPDATE `chatgpt_conversations`
               SET `deleted_at` = %s
               WHERE `convid` = %s;
            """
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Format the current time in the appropriate format
            cursor.execute(sql, (current_time, convid))
            # Commit the transaction to ensure the change is saved
            connection.commit()
            # Since it is an update operation, there is no need to return any query results
    finally:
        connection.close()

    # Return a JSON object indicating the operation was successful
    return json.dumps({
        "message": "Conversation archived successfully.",
        "success": True
    })
def guidang_conversations(user_token):
    # 连接数据库
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            # 获取当前时间，包括毫秒
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            # 仅更新 `deleted_at` 为 NULL 的指定用户的会话记录
            sql = """
                 UPDATE `chatgpt_conversations`
                 SET `deleted_at` = %s
                 WHERE `usertoken` = %s AND `deleted_at` IS NULL;
            """
            cursor.execute(sql, (current_time, user_token))
            # 提交事务以确保数据更新
            connection.commit()
    finally:
        connection.close()

    # 返回一个表示操作成功的 JSON 对象
    return json.dumps({
        "message": None,
        "success": True
    })
def update_conversation_title(convid, new_title):
    # 连接数据库
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            # 更新指定用户的会话标题
            sql = """
                UPDATE `chatgpt_conversations`
                SET `title` = %s
                WHERE `convid` = %s;
            """
            cursor.execute(sql, (new_title, convid))

            # 提交事务以确保数据更新操作被执行
            connection.commit()
            # 由于是更新操作，不需要返回任何查询结果
    finally:
        connection.close()

    # 返回一个表示操作成功的 JSON 对象
    return json.dumps({
        "message": "Title updated successfully",
        "success": True
    })
def update_json_title_with_db_title(json_string, convid):
    # 将传入的 JSON 字符串转换为字典
    try:
        json_data = json.loads(json_string)
    except json.JSONDecodeError as e:
        # 如果 json_string 不能转换为字典，则抛出错误
        raise ValueError("json_string is not a valid JSON string") from e

    # 连接数据库
    connection = None
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # 根据 convid 查询数据库中的 title
            sql = "SELECT `title` FROM `chatgpt_conversations` WHERE `convid` = %s;"
            cursor.execute(sql, (convid,))
            result = cursor.fetchone()

            # 如果查询到结果，则更新 JSON 数据中的 title
            if result:
                db_title = result['title']  # 假设结果是在元组的第一个位置
                json_data['title'] = db_title  # 更新 title
    except pymysql.MySQLError as e:
        # 处理数据库连接或操作失败的情况
        raise pymysql.MySQLError("Database connection or operation failed.") from e
    finally:
        # 确保无论如何都关闭数据库连接
        if connection:
            connection.close()

    # 将更新后的字典转换回 JSON 字符串
    updated_json_string = json.dumps(json_data)
    print (updated_json_string)
    return updated_json_string
def query_token_expire_time(token):
    # 连接数据库
    connection = pymysql.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            # 查询 token 的过期时间
            sql = "SELECT `expireTime` FROM `chatgpt_user` WHERE `userToken` = %s"
            cursor.execute(sql, (token,))
            result = cursor.fetchone()
            return result['expireTime'] if result else None
    finally:
        connection.close()
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)

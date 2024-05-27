from flask import Flask, request, jsonify
import requests
import datetime
import json

app = Flask(__name__)

@app.route('/api/validate_token', methods=['GET'])
def validate_token():
    xufeitoken = request.args.get('token')
    if not xufeitoken:
        return jsonify({'status': 'error', 'message': 'Token not provided'}), 400
    
    # 根据xufeitoken值构建文件名
    token_file = f"{xufeitoken}.txt"

    # 从对应文件读取续费天数
    renew_days = get_renew_days(token_file)
    if renew_days == 0:
        return jsonify({'status': 'error', 'message': 'No renewals needed or file not found'}), 403

    headers = {'Authorization': get_saved_token()}
    
    user_list_response = requests.post('http://23.224.111.139:8000/admin/chatgpt/user/page', json={"page": 1, "size": 1000}, headers=headers)
    user_list_data = user_list_response.json()
    
    valid_users = [user for user in user_list_data['data']['list'] if user['userToken'] == xufeitoken]
    if not valid_users:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404
    
    expire_time = datetime.datetime.now()
    new_expire_time = (expire_time + datetime.timedelta(days=renew_days)).strftime('%Y-%m-%d %H:%M:%S')

    latest_user = valid_users[0]

    update_data = {
        "userToken": xufeitoken,
        "expireTime": new_expire_time,
        "isPlus": 1,
        "remark": "",
        "createTime": latest_user['createTime'],
        "deleted_at": latest_user['deleted_at'],
        "id": latest_user['id'],
        "updateTime": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    update_response = requests.post('http://23.224.111.139:8000/admin/chatgpt/user/update', json=update_data, headers=headers)
    update_response_data = update_response.json()
    
    if update_response_data.get('code') == 1000:
        reset_renew_days(token_file)  # 将续费天数重置为0
        return jsonify({'status': 'success', 'message': '续费成功，最新到期时间:' + new_expire_time, 'code': '200'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Failed to update user'}), 400

def get_saved_token():
    try:
        with open('token.txt', 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        return "Token not found"

def get_renew_days(token_file):
    try:
        with open(token_file, 'r') as file:
            return int(file.read().strip())
    except (FileNotFoundError, ValueError):
        return 0  # If file does not exist or content is not an integer

def reset_renew_days(token_file):
    with open(token_file, 'w') as file:
        file.write('0')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001, debug=True)

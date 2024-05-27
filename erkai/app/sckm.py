from flask import Flask, request, jsonify
import requests
import datetime
from datetime import timedelta
import uuid
import json
import os

app = Flask(__name__)

@app.route('/api/validate_token', methods=['GET', 'POST'])
def validate_token():
    token = request.args.get('token', '')
    days = request.args.get('day', None)  # 获取day参数
    gongxiang = request.args.get('gongxiang', None)  # 获取gongxiang参数
    plus = request.args.get('plus', None) or '1'
    amount = int(request.args.get('amount', '1'))  # 获取amount参数，默认值为1

    if token == 'sharegpt':
        filename = ''
        count_filename = ''
        userToken_filename = ''
        generated_tokens = []

        for _ in range(amount):
            if gongxiang and days:
                try:
                    gongxiang_int = int(gongxiang)  # 将gongxiang转换为整数
                    days_int = int(days)  # 将days转换为整数
                    filename = f"{gongxiang_int}r{days_int}d.txt"
                    count_filename = f"{gongxiang_int}r{days_int}tcs.txt"
                    
                    if os.path.exists(count_filename):
                        with open(count_filename, 'r') as file:
                            count = int(file.read().strip())
                            if count <= 1:
                                # 次数耗尽时，创建新的token并重置次数
                                userToken = str(uuid.uuid4())
                                reset_count = gongxiang_int  # 重置次数为初始共享次数
                                with open(count_filename, 'w') as file:
                                    file.write(str(reset_count))
                                with open(filename, 'w') as file:
                                    file.write(userToken)
                                # 继续流程，使用新的token和重置后的次数
                            else:
                                # 减少次数并更新文件
                                count -= 1
                                with open(count_filename, 'w') as file:
                                    file.write(str(count))
                                if os.path.exists(filename):
                                    with open(filename, 'r') as file:
                                        userToken = file.read().strip()
                                        generated_tokens.append(userToken)
                                        continue
                    else:
                        # 初始化次数监测文件和token
                        userToken = str(uuid.uuid4())
                        with open(count_filename, 'w') as file:
                            file.write(str(gongxiang_int))
                        with open(filename, 'w') as file:
                            file.write(userToken)
                except ValueError:
                    return jsonify({'status': 'error', 'message': 'Invalid gongxiang or days value'}), 400

            userToken = str(uuid.uuid4())
            # Create and write to the new file using the userToken as filename
            userToken_filename = f"{userToken}.txt"
            with open(userToken_filename, 'w') as file:
                file.write(days if days else "30")  # Write the 'day' value, default to "30" if not provided

            headers = {
                'Authorization': get_saved_token()
            }
            
            expireTime = datetime.datetime.now() + timedelta(days=int(days) if days else 30)
            expireTime = expireTime.strftime('%Y-%m-%d %H:%M:%S')
            
            extra_data = json.loads(request.form.get('data', '{}'))
            contact = extra_data.get('order', {}).get('contact', '')
            pay_time = extra_data.get('order', {}).get('pay_time', '')
            trade_no = extra_data.get('order', {}).get('trade_no', '')
            biaoti = extra_data.get('commodity', {}).get('name', '')
            
            remark = f"购买的商品:{biaoti} 联系方式:{contact} 购买时间:{pay_time} 订单号:{trade_no}"
            print("Generated remark:", remark)

            data = {
                'userToken': userToken,
                'expireTime': expireTime,
                'isPlus': plus,
                'remark': remark
            }
            
            response = requests.post('http://23.224.111.139:8000/admin/chatgpt/user/add', json=data, headers=headers)
            response_data = response.json()
            
            if response_data.get('code') == 1000 and response_data.get('message') == "BaseResMessage":
                generated_tokens.append(userToken)
                if filename:
                    with open(filename, 'w') as file:
                        file.write(userToken)
            else:
                return jsonify({'status': 'error', 'message': 'Failed to add user'}), 400

        return jsonify({'status': 'success', 'userTokens': generated_tokens, 'code': '200'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Invalid token'}), 400

def get_saved_token():
    try:
        with open('token.txt', 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        print("token.txt not found. Ensure the token has been saved.")
        return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7999, debug=True)
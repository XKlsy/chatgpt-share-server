import requests
import base64
import time
from xml.etree import ElementTree as ET

def get_svg_text(base64_data):
    decoded_data = base64.b64decode(base64_data)
    svg_content = decoded_data.decode('utf-8')

    svg_xml = ET.fromstring(svg_content)
    text_elements = svg_xml.findall('.//{http://www.w3.org/2000/svg}text')
    verify_code = ''.join([te.text for te in text_elements if te.text.isdigit()])

    return verify_code

def login_and_save_token():
    try:
        # 获取验证码
        captcha_url = "http://23.224.111.139:8000/admin/base/open/captcha?height=40&width=150"
        response = requests.get(captcha_url)
        response.raise_for_status()  # 触发异常来处理非成功响应

        response_json = response.json()
        captcha_id = response_json['data']['captchaId']
        svg_data = response_json['data']['data']
        svg_base64 = svg_data.split(",")[1]

        verify_code = get_svg_text(svg_base64)

        # 登录
        login_url = "http://23.224.111.139:8000/admin/base/open/login"
        login_data = {
            "username": "admin",
            "password": "Xk1206..",
            "captchaId": captcha_id,
            "verifyCode": verify_code
        }
        login_response = requests.post(login_url, json=login_data)
        login_response.raise_for_status()  # 触发异常来处理非成功响应

        # 获取token
        token = login_response.json().get('data', {}).get('token', '')
        # 保存token到文件
        with open('token.txt', 'w') as file:
            file.write(token)
        print("登录成功，Token已保存。")
    except requests.RequestException as e:
        print("网络请求异常：", e)

if __name__ == "__main__":
    while True:
        login_and_save_token()
        # 等待60秒
        time.sleep(60)

import random
import requests
import json
import des_3
import hashlib
import urllib3
import time
from pathlib import Path
import os
from urllib.parse import urljoin

import rsa_encrypt as rsa
from config import 配置文件

# 关闭警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class 完美校园:

    def __init__(self,phone_num,password,device_id,
                 app_version=10583101,
                 user_agent='Mozilla/5.0 (Linux; Android 12; EBG-AN00 Build/HUAWEIEBG-AN00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/99.0.4844.88 Mobile Safari/537.36 Wanxiao/5.8.3',
                 phone_code='raphael',
                 sys_type='android',
                 sys_version='12',
                 phone_model='EBG-AN00'):

        """ 
        初始化CampusLogin对象并交换密钥
        :param phone_num: 完美校园登录账号（手机号）
        :param device_id: 设备ID，模拟器IMEI或其他方式获取的可用于完美校园登录的ID
        :param app_version: 完美校园app版本
        :param user_agent: 账密登录时所用的用户代理
        :param phone_code: 手机代号
        :param sys_type: 系统类型，android，ipad，iphone
        :param sys_version: 系统版本
        :param phone_model: 手机机型
        """
        self.login_info = {
            "phoneNum": phone_num,
            "deviceId": device_id,
            "appKey": "",
            "sessionId": "",
            "wanxiaoVersion": app_version,
            "userAgent": user_agent,
            "shebeixinghao": phone_code,
            "systemType": sys_type,
            "telephoneInfo": sys_version,
            "telephoneModel": phone_model
        }
        # 内存缓存
        self.parts_query = []
        self.parts = [] # [{id:2,name:1号公寓}]
        self.parts2rooms = {} # {"公寓ID",[所有寝室]} 
        self.powers = []
        
        # 配置文件
        self.config = 配置文件()
        self.config.account = self.login_info['phoneNum']
        self.config.password = password
        self.config.device_id = self.login_info['deviceId']
        self.config.save()

        # 功能请求headers
        self.pay_id = 0
        self.scool_code = 1332
        self.fun_headers = {
            'Host': 'h5cloud.17wanxiao.com:18443',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'User-Agent': self.login_info['userAgent'],
            'X-Requested-With': 'XMLHttpRequest',
            'Referer':'', # 来源地址
            'Cookie':self.config.cookie,
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }

    # 交换密钥
    def exchange_secret(self):
        rsa_keys = rsa.create_key_pair(1024)
        try:
            resp = requests.post(
                'https://app.17wanxiao.com/campus/cam_iface46/exchangeSecretkey.action',
                headers={'User-Agent': self.login_info['userAgent']},
                json={'key': rsa_keys[0]},
                verify=False,
                timeout=30
            )
            session_info = json.loads(rsa.rsa_decrypt(resp.text.encode(resp.apparent_encoding), rsa_keys[1]))
            self.login_info['sessionId'] = session_info['session']
            self.login_info['appKey'] = session_info['key'][:24]
        except Exception as e:
            raise e.__class__("完美校园交换密钥失败", e) # raise抛出

    # 获取TOKEN
    def get_token(self):
        # 登录前交换密钥
        self.exchange_secret()
        # 开始登录
        password_list = [des_3.des_3_encrypt(i, self.login_info['appKey'], '66666666') for i in self.config.password]
        login_args = {
            'appCode': 'M002',
            'deviceId': self.login_info['deviceId'],
            'netWork': 'wifi',
            'password': password_list,
            'qudao': 'guanwang',
            'requestMethod': 'cam_iface46/loginnew.action',
            'shebeixinghao': self.login_info['shebeixinghao'],
            'systemType': self.login_info['systemType'],
            'telephoneInfo': self.login_info['telephoneInfo'],
            'telephoneModel': self.login_info['telephoneModel'],
            'type': '1',
            'userName': self.login_info['phoneNum'],
            'wanxiaoVersion': self.login_info['wanxiaoVersion']
        }
        upload_args = {
            'session': self.login_info['sessionId'],
            'data': des_3.object_encrypt(login_args, self.login_info['appKey'])
        }
        try:
            resp = requests.post(
                'https://app.17wanxiao.com/campus/cam_iface46/loginnew.action',
                headers={'campusSign': hashlib.sha256(json.dumps(upload_args).encode('utf-8')).hexdigest()},
                json=upload_args,
                verify=False,
                timeout=30,
            ).json()

            if resp['result_']:
                return True,self.login_info['sessionId']
            return False,resp['message_']
        except Exception as e:
            return False,f"{e.__class__},{e}"

    # 获取cookie
    def get_cookie(self):
        params = {
            "customerId": random.randint(1000,1999),
            "systemType": self.login_info['systemType'],
            "UAinfo": "wanxiao",
            "versioncode": self.login_info['wanxiaoVersion'],
            "token": self.config.token
        }
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Connection': 'keep-alive',
            'Host': 'h5cloud.17wanxiao.com:18443',
            'User-Agent': self.login_info['userAgent'],
            'X-Requested-With': 'com.newcapec.mobile.ncp',
        }
        # 如果本地配置中存在cookie就加入进去
        if self.config.cookie:
            headers['Cookie'] = self.config.cookie
        # 开始获取
        try:

            temp_resp = requests.get(
                url='https://h5cloud.17wanxiao.com:18443/CloudPayment/user/pay.do',
                params = params,
                headers=headers,
                allow_redirects=False # 禁止跳转，跳转后找不到Cookie
            )
            # 2024年4月18日22点18分 end，按道理说应该若本地有旧cookie，请求时填上才是正确操作，但是不填不会犯错，所以我选择不填ok
            # print(temp_resp.status_code,temp_resp.cookies.get('SESSION'))
            # 951afdfb-9e0c-47ca-9bdb-5695d032b123
            # 2024年4月18日21点38分 ok 请求头cookie不要，第一次获得cookie，然后跳转让服务器知道cookie
            # 2024年4月18日20点50分 ok 确实禁止跳转，然后headers里面cookie是历史cookie。。。虽然这样可以用，但是？如果重新登录，历史cookie还有吗？
            if temp_resp.status_code == 302: # 跳转
                # 设置配置文件cookie
                self.config.cookie = f"SESSION={temp_resp.cookies.get('SESSION')}"
                redirect_url = urljoin('https://h5cloud.17wanxiao.com:18443/CloudPayment/user/pay.do', temp_resp.headers.get('Location')) # 跳转请求地址
                # 获取cookie | 进入云缴费界面了
                headers['Cookie'] = self.config.cookie
                resp = requests.get(
                    url=redirect_url,
                    headers = headers
                )
                try:
                    # 覆盖写入
                    with open('data/debug.html', 'w+') as f:
                        f.write(resp.text)
                except:
                        ""

                if resp.status_code == 200:
                    try:
                        type_resp = requests.get(f"https://h5cloud.17wanxiao.com:18443/CloudPayment/bill/selectPayProject.do?txcode=elecdetails&interurl=elecdetails&payProId={self.pay_id}&amtflag=0&payamt=100&payproname=%E7%94%A8%E7%94%B5%E6%94%AF%E5%87%BA&img=https://payicons.59wanmei.com/cloudpayment/images/project/img-nav_2.png&subPayProId=",
                                                 headers=headers)
                        print(type_resp.status_code)
                    except:
                        ""
                    return True,self.config.cookie
                else:
                    self.config.cookie = ""
                    return False,""

        except Exception as e:
            return False,f"{e.__class__},{e}"

    # 功能性请求
    def __get_fun(self,params,headers,url="https://h5cloud.17wanxiao.com:18443/CloudPayment/user/getRoom.do"):
        try:
            resp = requests.get(url=url,
                            params=params,
                            headers=headers)
            if resp.status_code == 200 and not ("-400" in resp.text) or not ("FAIL" in resp.text): # FAIL = 订单号异常
                return True,resp.json()
            return False,f"__get_fun请求失败{resp.status_code}"
        except Exception as e:
            # cookie过期，json()就会报错
            if 'code=ERROR' in resp.text:
                # self.pay_id = random.randint(1104,1110)
                # print(f"当前订单号为：{self.pay_id}")
                try:
                    res,msg = self.get_cookie()
                except:
                    # 先获取token、再获取cookie
                    res,msg = self.get_token()
                    if not res:
                        print(f"[TOKEN] {msg}")
                        return
                    self.config.token = msg
                
                    # 获取cookie / cookie失效的很快，更新一下又不亏
                    res,msg = self.get_cookie()
                    if not res:
                        print(f"[COOKIE] {msg}")
                        return
                    self.config.cookie = msg
                    self.config.save() #保存配置
                    return False,f"TOKEN过期，已更新，请现在重试"
                if res:
                    self.config.cookie = msg
                    self.fun_headers['Cookie'] = msg
                else:
                    self.config.cookie = ""
                self.config.save()
            return False,f"获取失败,{resp.text}"
    
    # 获取公寓ID
    def get_part_id(self):
        params = {
            'payProId': self.pay_id,
            'schoolcode': self.scool_code,
            'optype': '2',
            'areaid': '1',
            'buildid': '0',
            'unitid': '0',
            'levelid': '0',
            'businesstype': '2'
        }
        headers = self.fun_headers.copy() # 复制一份
        headers['Referer'] = f"https://h5cloud.17wanxiao.com:18443/CloudPayment/bill/selectPayProject.do?txcode=elecdetails&interurl=elecdetails&payProId={self.pay_id}&amtflag=0&payamt=100&payproname=%E7%94%A8%E7%94%B5%E6%94%AF%E5%87%BA&img=https://payicons.59wanmei.com/cloudpayment/images/project/img-nav_2.png&subPayProId="
        res,msg = self.__get_fun(params=params,headers=headers)
        if not res: # {"returncode":"-400","returnmsg":"云缴费平台接口返回信息为空"} 订单冲突了
            return False,msg
        return True,msg

    # 根据公寓ID获取所有房间信息
    def get_room_list(self,id):
        params = {
            'payProId': self.pay_id,
            'schoolcode': self.scool_code,
            'optype': '4',
            'areaid': '1',
            'buildid': id,
            'unitid': '0',
            'levelid': '-1',
            'businesstype': '2'
        }
        headers = self.fun_headers.copy() # 复制一份
        headers['Referer'] = f"https://h5cloud.17wanxiao.com:18443/CloudPayment/bill/selectPayProject.do?txcode=elecdetails&interurl=elecdetails&payProId={self.pay_id}&amtflag=0&payamt=100&payproname=%E7%94%A8%E7%94%B5%E6%94%AF%E5%87%BA&img=https://payicons.59wanmei.com/cloudpayment/images/project/img-nav_2.png&subPayProId="
        res,msg = self.__get_fun(params=params,headers=headers)
        if not res: # {'code': 'FAIL', 'msg': '云缴费平台接口返回信息为空'}
            return False,msg
        return True,msg
    
    # 根据房间ID获取电费信息
    def get_power_info(self,room_id):
        params = {
            'payProId': self.pay_id,
            'schoolcode': '1332', # 大学城校区
            'businesstype': '2',  # 未知
            'roomverify': room_id
        }
        headers = self.fun_headers.copy() # 复制一份
        headers['Referer'] = f"https://h5cloud.17wanxiao.com:18443/CloudPayment/bill/selectPayProject.do?txcode=elecdetails&interurl=elecdetails&payProId={self.pay_id}&amtflag=0&payamt=100&payproname=%E7%94%A8%E7%94%B5%E6%94%AF%E5%87%BA&img=https://payicons.59wanmei.com/cloudpayment/images/project/img-nav_2.png&subPayProId="
        res,msg = self.__get_fun(params=params,headers=headers,url="https://h5cloud.17wanxiao.com:18443/CloudPayment/user/getRoomState.do")
        if not res: # {'code': 'FAIL', 'msg': '云缴费平台接口返回信息为空'}
            return False,msg
        return True,msg

    # 低频数据更新
    def update_data_low(self,update_list = ['part','room']):
        for i in update_list:
            if i == "part":
                res,msg = self.get_part_id()
                if res:
                    try:
                        # 覆盖写入
                        with open('data/parts.json', 'w+') as f:
                            json.dump(msg, f)
                    except:
                        print(f"[UPDATE-PART] 写入失败")
                else:
                    print(f"[UPDATE-PART] {msg}")
                    return False
            
            if i == "room":
                # 文件读取公寓ID信息
                try:
                    with open('data/parts.json') as f:
                        self.parts = json.load(f)['roomlist']
                except:
                    print(f"[UPDATE-ROOM] 公寓ID读取失败")
                # 清空低频数据的内存缓存
                self.parts2rooms.clear()
                for part in self.parts:
                    part_id = part['id'] # 公寓ID
                    # 查询当前公寓所有寝室ID
                    res,msg = self.get_room_list(part_id)
                    if res:
                        try:
                            # 覆盖写入
                            with open(f'data/rooms_{part_id}.json', 'w+') as f:
                                json.dump(msg, f)
                        except:
                            print(f"[UPDATE-ROOM] 写入失败 id={part_id}")
                        # 更新内存缓存
                        self.parts2rooms.update({part_id:msg['roomlist']})
                    else:
                        print(f"[UPDATE-ROOM] {msg}")
                    # 休眠下，这网站太矫情了
                    time.sleep(5)

    # 高频数据更新
    def update_data_high(self, update_list=[2, 3, 16, 17, 30, 31, 32, 51]):
        for part_id in update_list:
            print(part_id)
            rooms = self.parts2rooms[part_id]
            print(rooms)
            for room in rooms:
                room_id = room['id']
                room_name = room['name']

                res, msg = self.get_power_info(room_id)
                if res:
                    try:
                        data = {room_name: msg['quantity']}
                    except:
                        data = {room_name: "0"}
                    print(room_id, data)
                    
                    # 读取现有的数据
                    file_path = f'data/power_{part_id}.json'
                    if Path(file_path).exists():
                        with open(file_path, 'r') as f:
                            existing_data = json.load(f)
                    else:
                        existing_data = []

                    # 追加新数据
                    existing_data.append(data)

                    # 将数据保存到 JSON 文件中
                    try:
                        with open(file_path, 'w') as f:
                            json.dump(existing_data, f, indent=4)
                    except:
                        print("[UPDATE-POWER] 保存数据失败")
                else:
                    print(f"[UPDATE-POWER] {msg}")

                time.sleep(0.5)

    # 这种json格式不正确 。。。。
    # def update_data_high(self, update_list=[2, 3, 16, 17, 30, 31, 32, 51]):
    #     for part_id in update_list:
    #         rooms = self.parts2rooms[part_id]
    #         for room in rooms:
    #             room_id = room['id']
    #             room_name = room['name']

    #             res, msg = self.get_power_info(room_id)
    #             if res:
    #                 data = {room_name: msg['quantity']}
    #                 print(room_id, data)

    #                 file_path = f'data/power_{part_id}.json'
    #                 try:
    #                     with open(file_path, 'a') as f:
    #                         f.write(json.dumps(data) + '\n')
    #                     print(f"[UPDATE-POWER] 完成公寓{part_id}数据")
    #                 except:
    #                     print("[UPDATE-POWER] 保存数据失败")
    #             else:
    #                 print(f"[UPDATE-POWER] {msg}")

    #             time.sleep(1)

    # def update_data_high(self, update_list=[2, 3, 16, 17, 30, 31, 32, 51]):
    #     # 这里不直接使用parts2rooms，因为想让他支持单独更新某一个公寓
    #     for part_id in update_list:  # 所有公寓ID
    #         rooms = self.parts2rooms[part_id]  # {id, name}
    #         # 根据寝室ID获取电费
    #         temp_list = []
    #         for room in rooms:
    #             room_id = room['id']
    #             room_name = room['name']

    #             res, msg = self.get_power_info(room_id)
    #             if res:
    #                 temp_list.append({room_name: msg['quantity']})
    #                 print(room_id,{room_name: msg['quantity']})
    #             else:
    #                 print(f"[UPDATE-POWER] {msg}")
    #             # 时间匆忙，对不住了
    #             time.sleep(1)

    #     # 将 temp_list 保存到 JSON 文件中
    #     try:
    #         with open(f'data/power_{part_id}.json', 'w+') as f:
    #             json.dump(temp_list, f)
    #             print(f"[UPDATE-POWER] 完成公寓{part_id}数据,长度{len(temp_list)}")
    #     except:
    #         ""

        

        

    # 本地缓存数据读取
    def update_from_local(self,update_list = ['part','room','power']):
        for i in update_list:
            if i == "part":
                # 文件读取公寓ID信息
                try:
                    with open('data/parts.json') as f:
                        self.parts = json.load(f)['roomlist']
                    print(f"[UPDATE-PART-LOCAL] 公寓ID本地缓存读取成功,长度{len(self.parts)}")
                    # print(self.parts)
                except:
                    print(f"[UPDATE-PART-LOCAL] 公寓ID读取失败")
                
                self.parts_query = {item['name'][:1]: item['id'] for item in self.parts}

            if i == "room":
                # 文件读取寝室ID
                for part in self.parts:
                    part_id = part['id']
                    try:
                        with open(f'data/rooms_{part_id}.json') as f:
                            rooms = json.load(f)['roomlist']
                            self.parts2rooms.update({part_id: rooms})
                            print(f"[UPDATE-ROOM-LOCAL] 公寓{part_id}所有寝室本地缓存读取成功,长度{len(rooms)}")
                    except Exception as e:
                        print(f"[UPDATE-ROOM-LOCAL] 公寓{part_id}所有寝室读取失败 {e}")

            if i == "power":
                for part in self.parts:
                    part_id = part['id']
                    part_name = part['name']
                    try:
                        with open(f'data/power_{part_id}.json') as f:
                            rooms = json.load(f)
                            self.powers.append({part_name:rooms})
                            print(f"[UPDATE-POWER-LOCAL] 公寓{part_id}所有寝室本地缓存读取成功,长度{len(rooms)}")
                    except Exception as e:
                        print(f"[UPDATE-POWER-LOCAL] 公寓{part_id}所有寝室读取失败 {e}")
    # 寝室号查询寝室号ID
    def query_room(self,room_name): # 6317
        part_id = self.parts_query[room_name[:1]]
        # self.parts2rooms = {} # {"公寓ID",[所有寝室]} 
        for pid,rooms in self.parts2rooms.items():
            if part_id == pid:
                for room in rooms:
                    if room['name'] == room_name:
                        print(room['id'])
                        return room['id']
        return -1

    # 开始运行
    def init(self):
        # 配置文件中不存在cookie或token
        if self.config.cookie == "" or self.config.token == "":
            # 先获取token、再获取cookie
            res,msg = self.get_token()
            if not res:
                print(f"[TOKEN] {msg}")
                return
            self.config.token = msg
        
            # 获取cookie / cookie失效的很快，更新一下又不亏
            res,msg = self.get_cookie()
            if not res:
                print(f"[COOKIE] {msg}")
                return
            self.config.cookie = msg
        self.config.save() #保存配置
        #random.randint(0,2)] #生成支付订单ID
        self.pay_id = 1104
        # 万事俱备、查询寝室电费需要具备 {楼栋号}{寝室号} 的对应ID
        # pay_id_list = [1104,1106,1108] # 订单号时好时坏，就这样吧
        print(f"当前订单号为：{self.pay_id}")
        # self.get_part_id() 获取公寓ID
        # self.get_room_list(37) # 获取所有房间ID
        print(self.get_power_info('1-31---11560')) # 获取电费信息
        # self.update_data_low(["room"]) # 更新低频数据
        # self.update_from_local()
        # self.update_data_high(['32'])#[part['id'] for part in self.parts])
        # self.update_from_local()
        # self.query_room('6317')


        #/usr/local/lib/python3.9/site-packages/pyecharts/render/templates
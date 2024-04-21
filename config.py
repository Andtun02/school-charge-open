import json

class 配置文件:
    def __init__(self):
        try:
            with open('config.json') as f:
                config = json.load(f)
        except:
            error = ""
        
        self.account = config['account']
        self.password = config['password']
        self.device_id = config['device_id']
        self.token = config['token']
        self.cookie = config['cookie']
        
    
    def save(self):
        config = {
            'account': self.account,
            'password': self.password,
            'device_id': self.device_id,
            'token': self.token,
            'cookie': self.cookie
        }

        try:
            with open('config.json', 'w') as f:
                json.dump(config, f)
        except:
            return False
        return True


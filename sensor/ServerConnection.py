
import string
import random
import requests
from urllib.parse import urlencode
import json
import datetime




class ServerConnection(object):
    def __init__(self, server_config):

        self.config = server_config

        if not self.config.get('credentials_path',None):
            raise Exception('credential_path_not_provided')
        if not self.config.get('url_base',None):
            raise Exception('server_url_base_not_provided')
        if not self.config.get('device_serial',None):
            raise Exception('device_serial_identifier_not_provided')

        if not self.config.get('post_url',None):
                self.config['post_url'] = self.config['url_base'] + '/newdata'
        if not self.config.get('ping_url',None):
                self.config['ping_url'] = self.config['url_base'] + '/stillhere'

        self.stats = {
            'consec_net_errs': 0,
            'push_attempts': 0,
            'push_failures': 0,
            'ping_attempts': 0,
            'ping_failures': 0,

        }
        self.ip = self._myIP()

        self.creds  = self._loadCredentials()

        if not self.config.get('params_url',None):
                self.config['params_url'] = self.config['url_base'] + '/sensorparams/' + self.creds['sensor_name']

    def getStats(self):
        return { k:self.stats[k] for k in self.stats }

    def httpOK(self,n):
        return n >= 200 and n < 300

    def ping(self):
        try:
            print('ping()')
            now = datetime.datetimenow()
            data = {
                'sensor_name': self.creds.get('sensor_name',''),
                'token': self.creds['token'],
                'source': 'kromek_d3s',
                'date': now.isoformat(),
                'source_ip': self.ip,
            }
            res = requests.post(self.config['ping_url'], data = data, timeout=20)
            self.stats['ping_attempts'] += 1
            if self.httpOK(res.status_code):
                self.stats['consec_net_errs'] = 0
            else:
                self.stats['consec_net_errs'] += 1
                self.stats['ping_failures'] += 1
            return res
        except:
            return None


    def push(self, sdata):
        print('uploadData()')
        now = datetime.datetime.now()

        data = {
            'sensor_data': sdata,
            'sensor_name': self.creds.get('sensor_name',''),
            'token': self.creds['token'],
            'source': 'kromek_d3s',
            'date': now.isoformat(),
            'source_ip': self.ip,
        }
        res = requests.post(self.config['post_url'], json = data, timeout=60)
        self.stats['push_attempts'] += 1
        if self.httpOK(res.status_code):
            self.stats['consec_net_errs'] = 0
        else:
            self.stats['consec_net_errs'] += 1
            self.stats['push_failures'] += 1
        return res


    def _myIP(self):
        try:
            return requests.get('https://ipinfo.io').json()['ip']
        except:
            return 'dunno'

    def getParams(self, params = {}):
        self._paramsLocalOverride(params)
        self._paramsRemoteOverride(params)

    def _paramsLocalOverride(self,params):
        fn = self.config['params_path']
        try:
            with open(fn,'r') as fh:
                data = json.loads(fh.read())
                for key in data:
                    print('Local override params[{0}] = {1}'.format(key,json.dumps(data[key])))
                    params[key] = data[key]
        except Exception as e:
            print('Got exception reading local overrides');
            print(e)


    def _paramsRemoteOverride(self,params):
        print('_paramsRemoteOverride')
        try:
            url = self.config['params_url'] + '?' + urlencode({'token':self.creds['token']})
            res = requests.get(url, timeout=30)
            if res.status_code == 200:
                data = res.json()
                for key in data:
                    print('Remote override params[{0}] = {1}'.format(key,json.dumps(data[key])))
                    params[key] = data[key]
            else:
                print('Got error code fetching params from server.')
        except Exception as e:
            print('Got exception fetching params.')
            print(e)


    def _selfProvision(self):
        print('_selfProvision')
        def randStr(n):
            return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(n))

        name = self.config.get('device_name',None)
        if name is None:
            name = "d3s_" + randStr(10)

        provtok = None
        with open(self.config['provisioning_token_path'],'r') as ptfh:
            provtok = json.load(ptfh)

        reqdata = {
            'serial_number': self.config['device_serial'],
            'provtok': provtok,
            'name': name,
        }
        print(reqdata)
        res = requests.post(self.config['url_base'] + '/setup/' + name, reqdata)
        print(res)
        if res.status_code == 200:
            resdata = res.json()
            return resdata
        return None


    def _loadCredentials(self):
        try:
            with open(self.config['credentials_path'],'r') as fh:
                creds = json.load(fh)
                return creds
        except Exception as e:
            print('Problem loading credentials')
            print(e)
            try:
                creds = self._selfProvision()
                if creds:
                    with open(self.config['credentials_path'],'w') as fh:
                        fh.write(json.dumps(creds))
                    return creds
                else:
                    print('Could not self-provision. Exiting.')
                    raise Exception('self_provisioning_bad_result_or_could_not_store')
            except Exception as f:
                print('Self provisioning failed.')
                raise Exception('self_provisioning_failed')





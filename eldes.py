"""Eldes client"""
import requests
import json
import datetime
import os.path
import time

class ApiError(Exception):
    """An API Error Exception"""

    def __init__(self, status):
        self.status = status

    def __str__(self):
        return "APIError: status={}".format(self.status)
    
class EldesClient:
    def __init__(self, username, password, hostDeviceId, refresh_token_file=None):
        self.username = username
        self.password = password
        self.hostDeviceId = hostDeviceId
        self.refresh_token = None
        self.refresh_token_file = refresh_token_file
        self.url = "https://cloud.eldesalarms.com:8083/api/"
        self._create_https_connection()
        self._login()
        self.last_update = {
            "devices": datetime.datetime.now() - datetime.timedelta(minutes = 6)
        }

    def _create_https_connection(self):
        self.httpsession = requests.Session()
        self.httpsession.headers["X-Requested-With"] = "XMLHttpRequest"
        self.httpsession.headers["User-Agent"] = "okhttp/3.11.0"
        self.httpsession.headers["Content-Type"] = "application/json; charset=UTF-8"
    
    def _post(self, endpoint, body):
        r = self.httpsession.post(self.url+endpoint, json=body, timeout=(5,10))
        if r.status_code == 401:
            self._update_refresh_token(None)
            self._login()
            r = self._post(endpoint, body)
        return r
    
    def _get(self,endpoint):
        r = self.httpsession.get(self.url+endpoint, timeout=(5,10))
        if r.status_code == 401:
            self._login()
            r = self._get(endpoint)
        return r

    def _load_refresh_token(self):
        if self.refresh_token_file is not None and os.path.isfile(self.refresh_token_file):
            with open(self.refresh_token_file,"r") as token_file:
                self.refresh_token = token_file.readline()
                if self.refresh_token == '':
                    self.refresh_token = None
        else:
            self.refresh_token = None

    def _update_refresh_token(self, token):
        self.refresh_token = token
        if self.refresh_token_file is not None:
            if self.refresh_token is None:
                os.remove(self.refresh_token_file)
            else:
                f = open(self.refresh_token_file,"w")
                f.write(token)
                f.close()

    def _update_token(self, token):
        if token is not None:
            self.httpsession.headers["Authorization"] = "Bearer " + token
        else:
            self.httpsession.headers.pop("Authorization")

    def _login(self):
        self._load_refresh_token()
        if self.refresh_token is None:
            login_request = {
                "email": self.username,
                "password": self.password,
                "hostDeviceId": self.hostDeviceId
            }
            r = self.httpsession.post(self.url+"auth/login", json=login_request, timeout=(5,10))
            if r.status_code == 200:
                self._update_token(r.json()['token'])
                self._update_refresh_token(r.json()['refreshToken'])
            else:
                raise ApiError(r.text)
        else:
            self._update_token(self.refresh_token)
            r = self._get("auth/token")
            if r.status_code == 200:
                self._update_token(r.json()['token'])
            else:
                self._update_refresh_token(None)
                self._login

    def _get_imei(self, location):
        self.get_devices()
        for device in self.devices["deviceListEntries"]:
            if device["name"] == location:
                return device["imei"]

    def _get_partitionIndex(self, location, partition):
        self.get_devices()
        for device in self.devices["deviceListEntries"]:
            if device["name"] == location:
                for part in device["partitions"]:
                    if part["name"] == partition:
                        return part["internalId"]

    def get_devices(self):
        if self.last_update["devices"] < datetime.datetime.now() - datetime.timedelta(minutes = 1):
            r = self._get("device/list?showSupportMessages=true")
            self.devices = json.loads(r.text)
            self.last_update["devices"] = datetime.datetime.now()
            return self.devices
        
    def is_partition_armed(self, location, partition):
        self.get_devices()
        for device in self.devices["deviceListEntries"]:
            if device["name"] == location:
                for part in device["partitions"]:
                    if part["name"] == partition:
                        return part["armed"]

    def partition_arm(self, location, partition):
        imei = self._get_imei(location)
        partitionIndex = self._get_partitionIndex(location, partition)
        arm_request = {
            "imei": imei,
            "partitionIndex": partitionIndex
        }
        r = self._post("device/action/arm", body=arm_request)
        if r.status_code == 202:
            self.last_update["devices"] = datetime.datetime.now() - datetime.timedelta(minutes = 6)
            time.sleep(2)
            return True
        else:
            raise ApiError(r.status_code)

    def partition_disarm(self, location, partition):
        imei = self._get_imei(location)
        partitionIndex = self._get_partitionIndex(location, partition)
        disarm_request = {
            "imei": imei,
            "partitionIndex": partitionIndex
        }
        r = self._post("device/action/disarm", body=disarm_request)
        if r.status_code == 202:
            self.last_update["devices"] = datetime.datetime.now() - datetime.timedelta(minutes = 6)
            time.sleep(2)
            return True
        else:
            raise ApiError(r.status_code)
    
    def get_temperatures(self, location):
        imei = self._get_imei(location)
        r = self._post('device/temperatures?imei='+imei,{})
        if r.status_code == 200:
            return r.json()
        else:
            raise ApiError(r.status_code)
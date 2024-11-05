import config
from pymongo import MongoClient

def get_database_euronext():
    CONNECTION_STRING = "mongodb://"+config.USER+":"+config.PASS+"@"+config.DB_IP_ADRESS+":27017/"+config.DB_USER
    client = MongoClient(CONNECTION_STRING)
    return client['agri_data']['euronext']

def get_database_physical():
    CONNECTION_STRING = "mongodb://"+config.USER+":"+config.PASS+"@"+config.DB_IP_ADRESS+":27017/"+config.DB_USER
    client = MongoClient(CONNECTION_STRING)
    return client['agri_data']['physique']

def get_database_production():
    CONNECTION_STRING = "mongodb://"+config.USER+":"+config.PASS+"@"+config.DB_IP_ADRESS+":27017/"+config.DB_USER
    client = MongoClient(CONNECTION_STRING)
    return client['agri_data']['production']

def get_database():
    CONNECTION_STRING = "mongodb://"+config.USER+":"+config.PASS+"@"+config.DB_IP_ADRESS+":27017/"+config.DB_USER
    client = MongoClient(CONNECTION_STRING)
    return client['cot_data']

def get_database_price():
    CONNECTION_STRING = "mongodb://"+config.USER+":"+config.PASS+"@"+config.DB_IP_ADRESS+":27017/"+config.DB_USER
    client = MongoClient(CONNECTION_STRING)
    return client['agri_data']

def get_database_dev_cond_france():
    CONNECTION_STRING = "mongodb://"+config.USER+":"+config.PASS+"@"+config.DB_IP_ADRESS+":27017/"+config.DB_USER
    client = MongoClient(CONNECTION_STRING)
    return client['agri_data']['dev_cond_france']

def get_database_dev_cond():
    CONNECTION_STRING = "mongodb://"+config.USER+":"+config.PASS+"@"+config.DB_IP_ADRESS+":27017/"+config.DB_USER
    client = MongoClient(CONNECTION_STRING)
    return client['agri_data']['dev_cond']
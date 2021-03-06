# -*- coding: utf-8 -*-
import pymongo
from re import sub
from decimal import Decimal
from pymongo import MongoClient
import numpy as np
import datetime
import matplotlib.pyplot as plt
import pandas as pd
import json
import sys
import ast
from datetime import datetime
import os
from sqlalchemy import *
import argparse
from pymongo import MongoClient, errors
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError, NotFound
import os
from google.cloud import datastore
from google.cloud import bigquery


#python RSI_analysis_BQ.py 'mysql+pymysql://igenie_readwrite:igenie@127.0.0.1/dax_project' 'PARAM_FINANCIAL_KEY_COLLECTION' 'igenie-project-key.json' 'pecten_dataset_test.RSI'

def RSI_main(args):
    RSI_table = pd.DataFrame()
    project_name, constituent_list,table_store,table_historical = get_parameters(args)
    from_date, to_date = get_timerange(args)
    table_store = args.table_storage
    from_date = datetime.strftime(from_date,'%Y-%m-%d %H:%M:%S') #Convert to the standard time format
    to_date = datetime.strftime(to_date,'%Y-%m-%d %H:%M:%S') 
    date = datetime.strftime(datetime.now().date(),'%Y-%m-%d %H:%M:%S') #Current time of analysis
    
    for constituent in constituent_list:
        
        if constituent=='M\xc3\xbcnchener R\xc3\xbcckversicherungs-Gesellschaft':
            constituent = 'Münchener Rückversicherungs-Gesellschaft'
        elif constituent=='Deutsche B\xc3\xb6rse':
            constituent = 'Deutsche Börse'

       
        constituent_name = get_constituent_id_name(constituent)[1]
        constituent_id = get_constituent_id_name(constituent)[0]  
        his = get_historical_price(project_name,table_historical,constituent,to_date)
        RSI_current,overbought_pct,oversold_pct,RSI_score = RSI_calculate(his,21)
        RSI_table = RSI_table.append(pd.DataFrame({'Constituent':constituent,'Constituent_name':constituent_name, 'Constituent_id':constituent_id, 'Current_RSI':round(RSI_current,2),'percentage_days_overbought':round(overbought_pct*100,2),'percentage_days_oversold':round(oversold_pct*100,2),'RSI_bull_score':RSI_score,'Table':'RSI analysis','Date_of_analysis':date,'From_date':from_date,'To_date':to_date,'Status':'active'},index=[0]),ignore_index=True)
    
    
    print "table done"
    update_result(table_store)
    print "update done"
    store_result(args,project_name, table_store,RSI_table)
    print "all done"
    

def RSI_calculate(his,n):
    
    delta = his['closing_price'].diff()
    dUp, dDown = delta.copy(), delta.copy()
    dUp[dUp < 0] = 0
    dDown[dDown > 0] = 0   
    #RolUp = pd.rolling_mean(dUp,window=n,center=False) 
    #RolDown = pd.rolling_mean(dDown,window=n,center=False).abs()
    RolUp = dUp.rolling(window=n).mean()
    RolDown = dDown.rolling(window=n).mean().abs()
    RS = RolUp/RolDown+0.0
    a=RS.shape[0]
    RSI = np.zeros(a)
    for i in np.arange(n,a):
        RSI[i] = 100-100/(1.0+RS[i])
    #If > 70: overbought signal, <30: oversold signal
    RSI_last_year = RSI[-252:]
    #print RSI[-90:]
    overbought = (RSI_last_year>=70)
    oversold = (RSI_last_year<=30)
    overbought_count = RSI_last_year[overbought].shape[0]
    oversold_count = RSI_last_year[oversold].shape[0]
    
    #Indicating the bullish signal
    if RSI[-1] > 70:
        RSI_score = 2
    elif RSI[-1] < 30:
        RSI_score = 1
    else: 
        RSI_score =0
        
    if overbought_count>oversold_count:
        RSI_score = RSI_score+1
    else: 
        RSI_score=RSI_score
    print float(RSI[-1])
    return float(RSI[-1]),overbought_count/252.0,oversold_count/252.0,RSI_score


def get_parameters(args):
    query = 'SELECT * FROM'+' '+ args.parameter_table + ';'
    print query
    parameter_table = pd.read_sql(query, con=args.sql_connection_string)
    project_name = parameter_table["PROJECT_NAME_BQ"].loc[parameter_table['SCRIPT_NAME']=='RSI_analysis'].values[0]
    
    #Obtain the constituent_list
    a = parameter_table['CONSTITUENT_LIST'].loc[parameter_table['SCRIPT_NAME']=='RSI_analysis']
    #print a
    constituent_list=np.asarray(ast.literal_eval((a.values[0])))
    
    #Obtain the table storing historical price
    table_historical = parameter_table["TABLE_COLLECT_HISTORICAL_BQ"].loc[parameter_table['SCRIPT_NAME']=='RSI_analysis'].values[0]
    print table_historical
    table_store = parameter_table['TABLE_STORE_ANALYSIS_BQ'].loc[parameter_table['SCRIPT_NAME']=='RSI_analysis'].values[0]
    return project_name, constituent_list,table_store,table_historical


#this makes all the out-dated data in the collection 'inactive'
##alter the status of collection
def update_result(table_store):
    #import os
    #os.system("Storage.py")
    storage = Storage(google_key_path='/Users/kefei/Documents/Igenie_Consulting/keys/igenie-project-key.json')
    storage = Storage(google_key_path='igenie-project-key.json')
    query = 'UPDATE `' + table_store +'` SET Status = "inactive" WHERE Status = "active"'

    try:
        result = storage.get_bigquery_data(query)
    except Exception as e:
        print(e) 

def store_result(args,project_name,table_store,result_df):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = args.service_key_path
    client = bigquery.Client()
    #Store result to bigquery
    result_df.to_gbq(table_store, project_id = project_name, chunksize=10000, verbose=True, reauth=False, if_exists='append',private_key=None)
    
 

#this obtains the historical price data as a pandas dataframe from source for one constituent. 
def get_historical_price(project_name,table_historical,constituent,to_date):
    #Obtain project name, table for historical data in MySQL
    #QUERY ='SELECT closing_price, date FROM '+ table_historical + ' WHERE Constituent= "'+constituent+'"'+ " AND date between TIMESTAMP ('2008-01-01 00:00:00 UTC') and TIMESTAMP ('2017-12-11 00:00:00 UTC') ;"
    QUERY ='SELECT closing_price, date FROM '+ table_historical + ' WHERE Constituent= "'+constituent+'"'+ " AND date between TIMESTAMP ('2009-01-01 00:00:00 UTC') and TIMESTAMP ('" + to_date + " UTC') ;"
   
    print QUERY
    his=pd.read_gbq(QUERY, project_id=project_name)
    his['date'] = pd.to_datetime(his['date'],format="%Y-%m-%dT%H:%M:%S") #read the date format
    his = his.sort_values('date',ascending=1).reset_index(drop=True)
    return his


def get_timerange(args):
    query = 'SELECT * FROM PARAM_READ_DATE WHERE STATUS = "active";'
    timetable = pd.read_sql(query, con=args.sql_connection_string)
    from_date = timetable['FROM_DATE'].loc[timetable['ENVIRONMENT']=='test']
    to_date = timetable['TO_DATE'].loc[timetable['ENVIRONMENT']=='test']
    return from_date[0], to_date[0]


def get_constituent_id_name(old_constituent_name):
    mapping = {}
    mapping["BMW"] = ("BMWDE8170003036" , "BAYERISCHE MOTOREN WERKE AG")
    mapping["Allianz"] = ("ALVDEFEI1007380" , "ALLIANZ SE")
    mapping["Commerzbank"] = ("CBKDEFEB13190" , "COMMERZBANK AKTIENGESELLSCHAFT")
    mapping["adidas"] = ("ADSDE8190216927", "ADIDAS AG")
    mapping["Deutsche Bank"] = ("DBKDEFEB13216" , "DEUTSCHE BANK AG")
    mapping["EON"] = ("EOANDE5050056484" , "E.ON SE")
    mapping["Lufthansa"] = ("LHADE5190000974" ,"DEUTSCHE LUFTHANSA AG")
    mapping["Continental"] = ("CONDE2190001578" , "CONTINENTAL AG")
    mapping["Daimler"] = ("DAIDE7330530056" , "DAIMLER AG")
    mapping["Siemens"] = ("SIEDE2010000581" , "SIEMENS AG")
    mapping["BASF"] = ("BASDE7150000030" , "BASF SE")
    mapping["Bayer"] = ("BAYNDE5330000056" , "BAYER AG")
    mapping["Beiersdorf"] = ("BEIDE2150000164" , "BEIERSDORF AG")
    mapping["Deutsche Börse"] = ("DB1DEFEB54555" , "DEUTSCHE BOERSE AG")
    mapping["Deutsche Post"] = ("DPWDE5030147191" , "DEUTSCHE POST AG")
    mapping["Deutsche Telekom"] = ("DTEDE5030147137" , "DEUTSCHE TELEKOM AG")
    mapping["Fresenius"] = ("FREDE6290014544" , "FRESENIUS SE & CO.KGAA")
    mapping["HeidelbergCement"] = ("HEIDE7050000100" , "HEIDELBERGCEMENT AG")
    mapping["Henkel vz"] = ("HEN3DE5050001329" , "HENKEL AG & CO. KGAA")
    mapping["Infineon"] = ("IFXDE8330359160" , "INFINEON TECHNOLOGIES AG")
    mapping["Linde"] = ("LINDE8170014684" , "LINDE AG")
    mapping["Merck"] = ("MRKDE6050108507" , "MERCK KGAA")
    mapping["ProSiebenSat1 Media"] = ("PSMDE8330261794" , "PROSIEBENSAT.1 MEDIA SE")
    mapping["RWE"] = ("RWEDE5110206610" , "RWE AG")
    mapping["SAP"] = ("SAPDE7050001788" , "SAP SE")
    mapping["thyssenkrupp"] = ("TKADE5110216866" , "THYSSENKRUPP AG")
    mapping["Vonovia"] = ("VNADE5050438829" , "VONOVIA SE")
    mapping["DAX"] = ("DAX", "DAX")
    mapping["Fresenius Medical Care"] = ("FMEDE8110066557" , "FRESENIUS MEDICAL CARE AG & CO.KGAA")
    mapping["Volkswagen (VW) vz"] = ("VOW3DE2070000543" , "VOLKSWAGEN AG")
    mapping["Münchener Rückversicherungs-Gesellschaft"] = ("MUV2DEFEI1007130" , "MUNCHENER RUCKVERSICHERUNGS - GESELLSCHAFT AKTIENGESELLSCHAFT IN MUNCHEN")

    if old_constituent_name in mapping:
        return mapping[old_constituent_name]
    else:
        return old_constituent_name


class Storage:
    def __init__(self, google_key_path=None, mongo_connection_string=None):
        if google_key_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_key_path
            self.bigquery_client = bigquery.Client()
        else:
            self.bigquery_client = None

        if mongo_connection_string:
            self.mongo_client = MongoClient(mongo_connection_string)
        else:
            self.mongo_client = None
            
    def get_bigquery_data(self, query, timeout=None, iterator_flag=True): 
        if self.bigquery_client:
            client = self.bigquery_client
        else:
            client = bigquery.Client()

        print("Running query...")
        query_job = client.query(query)
        iterator = query_job.result(timeout=timeout)

        if iterator_flag:
            return iterator
        else:
            return list(iterator)



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('sql_connection_string', help='The connection string to mysql for parameter table') 
    parser.add_argument('parameter_table',help="The name of the parameter table in MySQL")
    parser.add_argument('service_key_path',help='google service key path')
    parser.add_argument('table_storage',help='BigQuery table where the new data is stored')
    
    args = parser.parse_args()
    RSI_main(args)

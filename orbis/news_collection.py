import requests
import xml.etree.ElementTree as ET
import os
from datetime import datetime
from io import StringIO
import pandas as pd
import sys

#Deprecated
def get_orbis_news(user, pwd):
    soap = SOAPUtils()

    query = """" SELECT NEWS_DATE USING [Parameters.RepeatingDimension=NewsDim],
NEWS_TITLE USING [Parameters.RepeatingDimension=NewsDim],
NEWS_ARTICLE_TXT USING [Parameters.RepeatingDimension=NewsDim],
NEWS_COMPANIES USING [Parameters.RepeatingDimension=NewsDim],
NEWS_TOPICS USING [Parameters.RepeatingDimension=NewsDim],
NEWS_COUNTRY USING [Parameters.RepeatingDimension=NewsDim],
NEWS_REGION USING [Parameters.RepeatingDimension=NewsDim],
NEWS_SOURCE USING [Parameters.RepeatingDimension=NewsDim],
NEWS_PUBLICATION USING [Parameters.RepeatingDimension=NewsDim],
NEWS_ID USING [Parameters.RepeatingDimension=NewsDim] FROM RemoteAccess.A"""

    constituents = [('Allianz', 'DEFEI1007380'), ('adidas', 'DE8190216927'),
                    ('BASF', 'DE7150000030'), ('Bayer', 'DE5330000056'),
                    ('Beiersdorf', 'DE2150000164'), ("BMW", "DE8170003036"),
                    ('Continental', 'DE2190001578'), ('Commerzbank', 'DEFEB13190'),
                    ('Daimler', 'DE7330530056'), ("Deutsche Bank", "DEFEB13216"),
                    ('Deutsche Börse', 'DEFEB54555'), ('Deutsche Post', 'DE5030147191'),
                    ('Deutsche Telekom', 'DE5030147137'), ('EON', 'DE5050056484'),
                    ('Fresenius Medical Care', 'DE8110066557'),
                    ('Fresenius', 'DE6290014544'), ('HeidelbergCement', 'DE7050000100'),
                    ('Henkel vz', 'DE5050001329'), ('Infineon', 'DE8330359160'),
                    ('Linde', 'DE8170014684'), ('Lufthansa', 'DE5190000974'),
                    ('Merck', 'DE6050108507'),
                    ('Münchener Rückversicherungs-Gesellschaft', 'DEFEI1007130'),
                    ('ProSiebenSat1 Media', 'DE8330261794'), ('RWE', 'DE5110206610'),
                    ('SAP', 'DE7050001788'), ('Siemens', 'DE2010000581'),
                    ('thyssenkrupp', 'DE5110216866'), ('Volkswagen (VW) vz', 'DE2070000543'),
                    ('Vonovia', 'DE5050438829')]

    data = "all_news"

    for name, bvdid in constituents:
        token = soap.get_token(user, pwd, "orbis")
        if not token:
            return None
        try:
            selection_token = soap.find_by_bvd_id(token, bvdid, "orbis")
            get_data_result = soap.get_data(token, selection_token, "1", query, data, name, "orbis")
        except Exception as e:
            print(str(e))
        finally:
            soap.close_connection(token, "zephyr")

#Needs some work
def get_zephyr_ma_deals(user,pwd):
    query = ""
    soap = SOAPUtils()

    strategies = ["adidas_strategy",
                  "Allianz_strategy",
                  "BASF_strategy",
                  "Bayer_strategy",
                  "Beiersdorf_strategy",
                  "BMW_strategy",
                  "Commerzbank_strategy",
                  "Continental_strategy",
                  "Daimler_strategy",
                  "Deutsche_Boerse_strategy",
                  "Deutsche_Post_strategy",
                  "Deutsche_strategy",
                  "Deutsche_Telekom_strategy",
                  "EON_strategy",
                  "Fresenius_medical_strategy",
                  "Fresenius_strategy",
                  "HeidelbergCement_strategy",
                  "Henkel_strategy",
                  "Infineon_strategy",
                  "Linde_strategy",
                  "Lufthansa_strategy",
                  "Merck_strategy",
                  "Munchener_strategy",
                  "Prosiebel_strategy",
                  "RWE_strategy",
                  "SAP_strategy",
                  "Siemens_strategy",
                  "thyssenkrupp_strategy",
                  "Volkswagen_strategy",
                  "Vonovia_strategy"]

    data = "all_deals"

    for strategy in strategies:
        token = soap.get_token(user, pwd, "zephyr")
        if not token:
            return None
        try:
            selection_token, selection_count = soap.find_with_strategy(token, strategy, "zephyr")
            get_data_result = soap.get_data(token, selection_token, selection_count, long_query, data, strategy, "zephyr")
        except Exception as e:
            print(str(e))
        finally:
            soap.close_connection(token, "zephyr")

def get_historical_orbis_news(user, pwd, database, google_key_path, param_connection_string):
    soap = SOAPUtils()
    storage = Storage()

    fields = ["NEWS_DATE", "NEWS_TITLE", "NEWS_ARTICLE_TXT",
              "NEWS_COMPANIES", "NEWS_TOPICS", "NEWS_COUNTRY", "NEWS_REGION",
              "NEWS_LANGUAGE", "NEWS_SOURCE", "NEWS_PUBLICATION", "NEWS_ID"]

    filter = ["NEWS_DATE_NewsDim", "NEWS_TITLE_NewsDim", "NEWS_ARTICLE_TXT_NewsDim",
              "NEWS_COMPANIES_NewsDim", "NEWS_TOPICS_NewsDim", "NEWS_COUNTRY_NewsDim", "NEWS_REGION_NewsDim",
              "NEWS_LANGUAGE_NewsDim", "NEWS_SOURCE_NewsDim", "NEWS_PUBLICATION_NewsDim", "NEWS_ID_NewsDim"]

    columns = ["NAME", "ISIN"]

    constituents = storage.get_sql_data(sql_connection_string=param_connection_string,
                          sql_table_name="CONSTITUENTS_MASTER",
                          sql_column_list=columns)

    constituents = [('Allianz', 'DEFEI1007380')]

    for name, bvdid in constituents:

        file_name = "{}_historical_news.json".format(name)

        all_df = []

        i = 0
        while i < len(fields):
            print("i:{}".format(i))
            token = soap.get_token(user, pwd, database)
            query = "SELECT {} USING [Parameters.RepeatingDimension=NewsDim] FROM RemoteAccess.A".format(fields[i])
            selection_token, selection_count = soap.find_by_bvd_id(token, bvdid, database)
            print("Getting {} data".format(fields[i]))
            try:
                get_data_result = soap.get_data(token, selection_token, selection_count, query, fields[i], name, database)
            except Exception as e:
                print(str(e))
                continue
            finally:
                soap.close_connection(token, database)

            result = ET.fromstring(get_data_result)
            csv_result = result[0][0][0].text

            TESTDATA = StringIO(csv_result)

            if fields[i] == "NEWS_DATE":
                all_df.append(pd.read_csv(TESTDATA, sep=",", parse_dates=["NEWS_DATE_NewsDim"]))
            else:
                all_df.append(pd.read_csv(TESTDATA, sep=","))

            i += 1

        df = pd.concat(all_df, axis=1)
        df = df[filter]
        df.columns = fields
        df.to_json(file_name, orient="records", date_format="iso")

        # Save to MongoDB

        # Save to cloud
        if os.path.isfile(file_name):
            cloud_destination = "2017/{}".format(file_name)
            if storage.upload_to_cloud_storage(google_key_path,"igenie-news", file_name,cloud_destination):
                os.remove(file_name)
            else:
                print("File not uploaded to Cloud storage.")
        else:
            print("File does not exists in the local filesystem.")

def get_daily_orbis_news(user, pwd, database, google_key_path, param_connection_string):
    soap = SOAPUtils()
    storage = Storage()

    fields = ["NEWS_DATE", "NEWS_TITLE", "NEWS_ARTICLE_TXT",
              "NEWS_COMPANIES", "NEWS_TOPICS", "NEWS_COUNTRY", "NEWS_REGION",
              "NEWS_LANGUAGE", "NEWS_SOURCE", "NEWS_PUBLICATION", "NEWS_ID"]

    filter = ["NEWS_DATE_NewsDim", "NEWS_TITLE_NewsDim", "NEWS_ARTICLE_TXT_NewsDim",
              "NEWS_COMPANIES_NewsDim", "NEWS_TOPICS_NewsDim", "NEWS_COUNTRY_NewsDim", "NEWS_REGION_NewsDim",
              "NEWS_LANGUAGE_NewsDim", "NEWS_SOURCE_NewsDim", "NEWS_PUBLICATION_NewsDim", "NEWS_ID_NewsDim"]

    columns = ["NAME", "ISIN"]

    constituents = storage.get_sql_data(sql_connection_string=param_connection_string,
                                        sql_table_name="CONSTITUENTS_MASTER",
                                        sql_column_list=columns)

    for name, bvdid in constituents:
        file_name = "{}_{}".format(name, str(datetime.datetime.today().date()))
        token = soap.get_token(user, pwd, database)
        selection_token, selection_count = soap.find_by_bvd_id(token, bvdid, database)

        try:
            get_report_section_result = soap.get_report_section(token,selection_token,selection_count,
                                                           database,"BVDNEWS")
        except Exception as e:
            print(str(e))
        finally:
            soap.close_connection(token, database)

        result = ET.fromstring(get_report_section_result)
        csv_result = result[0][0][0].text

        TESTDATA = StringIO(csv_result)
        df = pd.read_csv(TESTDATA, sep=",", parse_dates=["NEWS_DATE_NewsDim"])
        df = df[filter]
        df.columns = fields

        #Filter today's news only
        d = datetime.datetime.today() - datetime.timedelta(days=1)
        df = df.loc[df["NEWS_DATE"] > d.date()]

        df.to_json(file_name, orient="records", date_format="iso")

        # Save to MongoDB

        # Save to cloud
        if os.path.isfile(file_name):
            cloud_destination = "2017/{}".format(file_name)
            if storage.upload_to_cloud_storage(google_key_path,"igenie-news", file_name,cloud_destination):
                os.remove(file_name)
            else:
                print("File not uploaded to Cloud storage.")
        else:
            print("File does not exists in the local filesystem.")

#Development halted for now
def main_rest(api_key):
    constituents = [("BMW", "DE8170003036"), ("Commerzbank", "DEFEB13190"),
                    ("Deutsche Bank", "DEFEB13216"),
                    ("EON", "DE5050056484")]

    url = 'https://webservices.bvdep.com/rest/orbis/getdata'
    headers = {'apitoken': api_key, "Accept": "application/json, text/javascript, */*; q=0.01"}

    const = [("BMW", "DE8170003036")]

    for name, id in const:
        payload = {'bvdids': id}

        data = {"BvDIds":[id],
                "QueryString":"SELECT NEWS_DATE USING [Parameters.RepeatingDimension=NewsDim], NEWS_TITLE USING [Parameters.RepeatingDimension=NewsDim],NEWS_ARTICLE_TXT USING [Parameters.RepeatingDimension=NewsDim],NEWS_COMPANIES USING [Parameters.RepeatingDimension=NewsDim],NEWS_TOPICS USING [Parameters.RepeatingDimension=NewsDim],NEWS_COUNTRY USING [Parameters.RepeatingDimension=NewsDim],NEWS_REGION USING [Parameters.RepeatingDimension=NewsDim],NEWS_LANGUAGE USING [Parameters.RepeatingDimension=NewsDim],NEWS_SOURCE USING [Parameters.RepeatingDimension=NewsDim],NEWS_PUBLICATION USING [Parameters.RepeatingDimension=NewsDim],NEWS_ID USING [Parameters.RepeatingDimension=NewsDim] FROM RemoteAccess.A"}

        response = requests.post(url, headers=headers, data=data, params=payload)

        if response.status_code != requests.codes.ok:
            print(response.text)
            return None

        result = response.text
        file_name = "{}_{}.xml".format(name, "all_news")
        directory = os.path.join(".", "data", file_name)
        with open(str(directory), 'w') as f:
            f.write(result)
        return True

def main(args):
    #get_zephyr_data(args.user,args.pwd)
    #get_orbis_news(args.user,args.pwd)
    get_historical_orbis_news(args.user,args.pwd, "orbis", args.google_key_path)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('python_path', help='The connection string')
    parser.add_argument('google_key_path', help='The path of the Google key')
    parser.add_argument('param_connection_string', help='The MySQL connection string')
    parser.add_argument('user', help='SOAP user')
    parser.add_argument('pwd', help='SOAP pwd')
    args = parser.parse_args()
    sys.path.insert(0, args.python_path)
    from utils.Storage import Storage
    from utils.SOAPUtils import SOAPUtils
    main(args)

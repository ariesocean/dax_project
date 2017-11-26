from pymongo import MongoClient, DESCENDING
from pprint import pprint
import bson
from bson.son import SON
from datetime import datetime
from langdetect import detect
import time

#for all_news
def get_all_news():
    client = MongoClient("mongodb://igenie_readwrite:igenie@35.189.89.82:27017/dax_gcp")
    db = client["dax_gcp"]
    all_news_landing = db["all_news_landing"]
    all_news = db["all_news"]

    constituents = list(all_news_landing.distinct("constituent_id"))

    from_date = datetime(2017, 11, 10)
    to_date = datetime(2017, 11, 16)

    for const in constituents:
        if const:
            data = list(all_news_landing.find({"constituent_id": const,
                                               "NEWS_DATE_NewsDim": {"$gte": from_date, "$lte": to_date}})
                        .sort("NEWS_DATE_NewsDim", DESCENDING)
                        .limit(10)
                        )
            to_insert = []
            for news in data:
                if detect(news["NEWS_TITLE_NewsDim"]) == 'en' and len(to_insert) < 3:
                    to_insert.append(news)
            #all_news.insert_many(to_insert)
            all_news.insert_one(to_insert[0])

#for news_analytics_assoc_orgs
def get_news_analytics_assoc_orgs(from_date, to_date):
    print("news_analytics_assoc_orgs")
    final_result = []
    client = MongoClient("mongodb://igenie_readwrite:igenie@35.189.89.82:27017/dax_gcp")
    db = client["dax_gcp"]
    all_news_landing = db["all_news_landing"]
    news_analytics_assoc_orgs = db["news_analytics_assoc_orgs"]

    constituents = list(all_news_landing.distinct("constituent_id"))
    constituents = list(filter(None.__ne__, constituents))
    #constituents = [constituents]

    for const in constituents:
        print(const)
        pipeline = [
            {
                "$match": {
                    "constituent_id": const,
                    "NEWS_DATE_NewsDim": {"$gte": from_date, "$lte": to_date},
                    "show":True
                }
            },
            {
                "$project": {
                    "constituent_id": "$constituent_id",
                    "constituent_name":"$constituent_name",
                    "org_tags": "$entity_tags.ORG",
                    "constituent": "$constituent"
                }
            },
            {"$unwind": "$org_tags"},
            {
                "$group": {
                    "_id": {"constituent_id": "$constituent_id", "org_tags": "$org_tags",
                            "constituent_name": "$constituent_name", "constituent": "$constituent"},
                    "count": {"$sum": 1}
                }
            },
            {"$sort": SON([("count", -1)])},
            {
                "$project":{
                    "_id":0,
                    "constituent_id":"$_id.constituent_id",
                    "constituent_name":"$_id.constituent_name",
                    "org_tags":"$_id.org_tags",
                    "count":"$count",
                    "constituent": "$_id.constituent",
                    "date":datetime.now()
                }
            }
        ]

        results = list(all_news_landing.aggregate(pipeline))
        to_return = []
        for r in results:
            if r["constituent"].lower() in r["org_tags"].lower() or \
                r["constituent_name"].lower() in r["org_tags"].lower() or \
                r["org_tags"].lower() in r["constituent"].lower() or \
                r["org_tags"].lower() in r["constituent_name"].lower() or \
                " AG".lower() in r["org_tags"].lower() or \
                len(r["org_tags"].split(" ")) > 3 or r["count"] < 2 or \
                r["org_tags"].lower() == "Trends".lower() or \
                r["org_tags"].lower() == "Share".lower():
                continue
            else:
                to_return.append(r)

        if to_return:
            if len(to_return) < 5:
                # final_result.append(to_return)
                news_analytics_assoc_orgs.insert_many(to_return)
            else:
                # final_result.append(to_return[:5])
                news_analytics_assoc_orgs.insert_many(to_return[:5])

        time.sleep(3)

    #return final_result

# for news_analytics_topic_sentiment
def get_news_analytics_topic_sentiment(from_date, to_date):
    print("news_analytics_topic_sentiment")
    final_result = []
    client = MongoClient("mongodb://igenie_readwrite:igenie@35.189.89.82:27017/dax_gcp")
    db = client["dax_gcp"]
    all_news_landing = db["all_news_landing"]
    news_analytics_topic_sentiment = db["news_analytics_topic_sentiment"]

    constituents = list(all_news_landing.distinct("constituent_id"))
    constituents = list(filter(None.__ne__, constituents))

    for const in constituents:
        print(const)
        pipeline = [
            {
                "$match": {
                    "constituent_id": const,
                    "NEWS_DATE_NewsDim": {"$gte": from_date, "$lte": to_date},
                    "score":{"$gte":0.25},
                    "categorised_tag":{"$nin":["NA"]}
                }
            },
            {"$unwind": "$categorised_tag"},
            {
                "$group": {
                    "_id": {"constituent_id": "$constituent_id", "categorised_tag": "$categorised_tag",
                            "constituent_name": "$constituent_name", "constituent": "$constituent"},
                    "count": {"$sum": 1}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "constituent_id": "$_id.constituent_id",
                    "constituent_name": "$_id.constituent_name",
                    "categorised_tag": "$_id.categorised_tag",
                    "count": "$count",
                    "constituent": "$_id.constituent",
                    "date": datetime.now(),
                    "overall_sentiment": "positive"
                }
            },
            {
                "$match": {
                    "count": {"$gte": 5}
                }
            }
        ]

        positive_results = list(all_news_landing.aggregate(pipeline))
        positive_dict = {}
        for item in positive_results:
            positive_dict[item["categorised_tag"]] = item

        #negative counts
        pipeline = [
            {
                "$match": {
                    "constituent_id": const,
                    "NEWS_DATE_NewsDim": {"$gte": from_date, "$lte": to_date},
                    "score": {"$lte": -0.25},
                    "categorised_tag": {"$nin": ["NA"]}
                }
            },
            {"$unwind": "$categorised_tag"},
            {
                "$group": {
                    "_id": {"constituent_id": "$constituent_id", "categorised_tag": "$categorised_tag",
                            "constituent_name": "$constituent_name", "constituent": "$constituent"},
                    "count": {"$sum": 1}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "constituent_id": "$_id.constituent_id",
                    "constituent_name": "$_id.constituent_name",
                    "categorised_tag": "$_id.categorised_tag",
                    "count": "$count",
                    "constituent": "$_id.constituent",
                    "date": datetime.now(),
                    "overall_sentiment":"negative"
                }
            },
            {
                "$match":{
                    "count":{"$gte":5}
                }
            }
        ]

        negative_results = list(all_news_landing.aggregate(pipeline))
        negative_dict = {}
        for item in negative_results:
            negative_dict[item["categorised_tag"]] = item

        final_result = []

        for key in set(positive_dict.keys()) | set(negative_dict.keys()):
            if key in positive_dict and key not in negative_dict:
                final_result.append(positive_dict[key])
            elif key in negative_dict and key not in positive_dict:
                final_result.append(negative_dict[key])
            elif key in positive_dict and key in negative_dict:
                if positive_dict[key]["count"] >= negative_dict[key]["count"]:
                    final_result.append(positive_dict[key])
                else:
                    final_result.append(negative_dict[key])

        final_result.sort(key=lambda x: x["count"], reverse=True)

        if final_result:
            if len(final_result) < 5:
                news_analytics_topic_sentiment.insert_many(final_result)
            else:
                news_analytics_topic_sentiment.insert_many(final_result)

        time.sleep(3)

#for news_sentiment_by_tag
def get_news_sentiment_by_tag(from_date, to_date):
    print("news_sentiment_by_tag")
    final_result = []
    client = MongoClient("mongodb://igenie_readwrite:igenie@35.189.89.82:27017/dax_gcp")
    db = client["dax_gcp"]
    all_news_landing = db["all_news_landing"]
    news_sentiment_by_tag = db["news_sentiment_by_tag"]

    constituents = list(all_news_landing.distinct("constituent_id"))
    constituents = list(filter(None.__ne__, constituents))

    for const in constituents:
        print(const)
        pipeline = [
            {
                "$match": {
                    "constituent_id": const,
                    "NEWS_DATE_NewsDim": {"$gte": from_date, "$lte": to_date},
                    "categorised_tag": {"$nin": ["NA"]}
                }
            },
            {"$unwind": "$categorised_tag"},
            {
                "$project": {
                    "categorised_tag":1,
                    "constituent_id": 1,
                    "constituent": 1,
                    "day": {"$dayOfYear":"$NEWS_DATE_NewsDim"},
                    "date": "$NEWS_DATE_NewsDim",
                    "score":"$score"
                }
            },
            {
                "$group": {
                    "_id": {"categorised_tag": "$categorised_tag",
                            "day":"$day",
                            "constituent_id": "$constituent_id",
                            "constituent": "$constituent",
                            "date":"$date"},
                    "avg_sentiment": {"$avg": "$score"}
                }
            },
            {"$sort": SON([("categorised_tag", -1)])},
            {
                "$project": {
                    "_id":0,
                    "avg_sentiment":1,
                    "categorised_tag":"$_id.categorised_tag",
                    "constituent_id": "$_id.constituent_id",
                    "constituent": "$_id.constituent",
                    "date": "$_id.date"
                }
            }
        ]

        result = list(all_news_landing.aggregate(pipeline))
        news_sentiment_by_tag.insert_many(result)
        time.sleep(3)

# for news_analytics_daily_sentiment
def get_news_analytics_daily_sentiment(from_date, to_date):
    print("news_analytics_daily_sentiment")
    final_result = []
    client = MongoClient("mongodb://igenie_readwrite:igenie@35.189.89.82:27017/dax_gcp")
    db = client["dax_gcp"]
    all_news_landing = db["all_news_landing"]
    news_analytics_daily_sentiment = db["news_analytics_daily_sentiment"]

    constituents = list(all_news_landing.distinct("constituent_id"))
    constituents = list(filter(None.__ne__, constituents))

    for const in constituents:
        print(const)
        pipeline = [
            {
                "$match": {
                    "constituent_id": const,
                    "NEWS_DATE_NewsDim": {"$gte": from_date, "$lte": to_date}
                }
            },
            {
                "$project": {
                    "constituent_id": 1,
                    "constituent": 1,
                    "constituent_name": 1,
                    "day": {"$dayOfYear": "$NEWS_DATE_NewsDim"},
                    "date": "$NEWS_DATE_NewsDim",
                    "score": "$score"
                }
            },
            {
                "$group": {
                    "_id": {"categorised_tag": "$categorised_tag",
                            "day": "$day",
                            "constituent_id": "$constituent_id",
                            "constituent": "$constituent",
                            "constituent_name": "$constituent_name",
                            "date": "$date"},
                    "avg_sentiment": {"$avg": "$score"}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "avg_sentiment": 1,
                    "categorised_tag": "$_id.categorised_tag",
                    "constituent_id": "$_id.constituent_id",
                    "constituent": "$_id.constituent",
                    "constituent_name": "$_id.constituent_name",
                    "date": "$_id.date"
                }
            }
        ]

        result = list(all_news_landing.aggregate(pipeline))
        news_analytics_daily_sentiment.insert_many(result)
        time.sleep(3)

def main(args):
    from_date = datetime(2017, 10, 1)
    to_date = datetime(2017, 11, 16)
    #get_news_analytics_assoc_orgs(from_date, to_date)
    #get_news_analytics_topic_sentiment(from_date, to_date)
    #get_news_sentiment_by_tag(from_date, to_date)
    #get_news_analytics_daily_sentiment(from_date, to_date)

if __name__ == "__main__":
    main(None)
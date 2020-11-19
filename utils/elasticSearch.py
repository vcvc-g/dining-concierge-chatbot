
import json
import boto3
import requests



def OuputPrint(ID):
    res = {}
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('YelpRestaurant').scan()['Items']
    for row in table:
        if(row['id'] == ID) : 
            res['name'] = row['name']
            res['rating'] = row['rating']
            res['cuisine'] = row['cuisine']
            res['phone'] = row['phone']
            res['location'] = row['location']['display_address'][0]+ row['location']['display_address'][1]
            res[ 'latitude']= row[ 'coordinates']['latitude']
            res['longitude'] = row[ 'coordinates']['longitude']
            break
    return res






def elasticSearch(cuisine):
    
    url = 'https://search-restaurant-h7ulkzrow4p43uscsdms7uhnqu.us-east-1.es.amazonaws.com/restaurants/restaurant/_search?from=0'+'&&size=1&&q=Cuisine:' + cuisine
    resp = requests.get(url, headers={"Content-Type": "application/json"}).json()
    print(url)
    if( not resp['hits']['hits']):
        print("We dont have such cuisine type!")
        return

    ID =resp['hits']['hits'][0]['_source']['RestaurantID']
    res = OuputPrint(ID)
    return res 
    

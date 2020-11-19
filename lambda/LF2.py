'''
 1. Pulls a message from the SQS queue (Q1), 
 2. Gets a random restaurant recommendation for the cuisine collected through conversation 
    from ElasticSearch and DynamoDB
 3. Formats restaurant recommendation
 4. Sends recommendation over text message to the phone number included in the SQS message, using SNS
'''

import logging
import sys
import time
import os
import json
import boto3
from botocore.vendored import requests
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)
sqs = boto3.client('sqs')
sqs_url = 'https://sqs.us-east-1.amazonaws.com/786146655581/botQueue'
ses = boto3.client('ses')
SENDER = 'qg2192@columbia.edu'

sns = boto3.client('sns')
sns_arn = 'arn:aws:sns:us-east-1:786146655581:bot_sendNotification'



def poll_sqs_message():

    try:
        response = sqs.receive_message(
            QueueUrl=sqs_url,
            AttributeNames=[
                'SentTimestamp'
            ],
            MaxNumberOfMessages=1,
            MessageAttributeNames=[
                'All'
            ],
            VisibilityTimeout=0,
            WaitTimeSeconds=0
        )

        print("----------")
        print(response)
        print("----------")

        message = response['Messages'][0]
        msg_body = message['Body']
        receipt_handle = message['ReceiptHandle']
        Delete received message from queue
        sqs.delete_message(
            QueueUrl=sqs_url,
            ReceiptHandle=receipt_handle
        )
        print('Received and deleted message: %s' % msg_body)
    
    except ClientError as error:
        logger.exception("Couldn't receive messages from queue")
        raise error

    else:
        return msg_body


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
    
    print("================")
    print(resp)
    print("================")

    
    if( not resp['hits']['hits']):
        print("We dont have such cuisine type!")
        return

    # 写一堆hit是因为resp返回一堆东西：  print(resp) for more detail
    ID =resp['hits']['hits'][0]['_source']['RestaurantID']
    res = OuputPrint(ID) # call 上面的helper method
    
    return res 
    

def sns_send_email(email_addr):

    SUBJECT = 'Resturant Suggestion From Dining Concierge Chatbot!'
    BODY_TEXT = ("Amazon SES Test (Python)\r\n"
                 "This email was sent with Amazon SES using the "
                 "AWS SDK for Python (Boto)."
                )
    BODY_HTML = """<html>
    <head></head>
    <body>
      <h1>Amazon SES Test (SDK for Python)</h1>
      <p>This email was sent with
        <a href='https://aws.amazon.com/ses/'>Amazon SES</a> using the
        <a href='https://aws.amazon.com/sdk-for-python/'>
          AWS SDK for Python (Boto)</a>.</p>
    </body>
    </html>
                """     


    try:
        #Provide the contents of the email.
        response = ses.send_email(
            Destination={
                'ToAddresses': [
                    email_addr,
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': "UTF-8",
                        'Data': BODY_HTML,
                    },
                    'Text': {
                        'Charset': "UTF-8",
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': "UTF-8",
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,
        )
    # Display an error if something goes wrong. 
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])
        

def lambda_handler(event, context):

    # Poll message from sqs and collect info
    message = poll_sqs_message()
    if not message:
        return
    location, cuisine, date, reserve_time, num_people, email = message.split(',')

    print('-----------------------')
    print(email)
    print('-----------------------')

    # Search recommendation over DB
    res = elasticSearch(cuisine)

    print('-----------------------')
    print(res)
    print('-----------------------')

    # TODO Send recommendation text message 
    # sns_send_email(email)
    
    SUBJECT = 'Resturant Suggestion From Dining Concierge Chatbot!'
                
    basic_info = "Hello! Here are my {} restaurant suggestions for {} people, for {} at {} pm: ".format(cuisine,num_people,date,reserve_time)
    recom_info = "{}, located at {}. Their phone number is {}.".format(res['name'],res['location'],res['phone'])
    
    body_text = basic_info+recom_info   
    body_html = """<html>
    <head></head>
    <body>
      <h1>Resturant Suggestion From Dining Concierge Chatbot!</h1>
      <p>{}{}</p>
    </body>
    </html>
                """.format(basic_info,recom_info)


    try:
        #Provide the contents of the email.
        response = ses.send_email(
            Destination={
                'ToAddresses': [
                    email,
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': "UTF-8",
                        'Data': body_html,
                    },
                    'Text': {
                        'Charset': "UTF-8",
                        'Data': body_text,
                    },
                },
                'Subject': {
                    'Charset': "UTF-8",
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,
        )
    # Display an error if something goes wrong. 
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])
        
    
    

    return





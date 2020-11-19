import math
import dateutil.parser
import datetime
import time
import os
import logging
import re 
import boto3


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
sqs = boto3.client('sqs')
sqs_url = 'https://sqs.us-east-1.amazonaws.com/786146655581/botQueue'


""" --- Helpers to build responses which match the structure of the necessary dialog actions --- """


def get_slots(intent_request):
    return intent_request['currentIntent']['slots']
    

def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


""" --- Helper Functions --- """


def parse_int(n):
    try:
        return int(n)
    except ValueError:
        return float('nan')


def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            "isValid": is_valid,
            "violatedSlot": violated_slot,
        }

    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }


def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False


def isvalid_phone(phone_number):
    if len(str(phone_number)) not in [7,10,11]:
        return False
    return True

def isvalid_email(address):
    regex = '^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$'
    if re.search(regex, address):
        return True
    return False


def validate_reservation(location, num_people, date, reserve_time, email):
    # flower_types = ['lilies', 'roses', 'tulips']
    # if flower_type is not None and flower_type.lower() not in flower_types:
    #     return build_validation_result(False,
    #                                    'FlowerType',
    #                                    'We do not have {}, would you like a different type of flower?  '
    #                                    'Our most popular flowers are roses'.format(flower_type))


    if num_people is not None:
    	if int(num_people) <= 0:
    		return build_validation_result(False, 'num_people', "Sorry, please enter a valid group number")

    if date is not None:
        if not isvalid_date(date):
            return build_validation_result(False, 'date', 'I did not understand that, what date would you like to make your reservation?')
        elif datetime.datetime.strptime(date, '%Y-%m-%d').date() < datetime.date.today():
            return build_validation_result(False, 'date', 'Stop tricking me, you can only make reservation from today onwards.  What day would you like?')

    if reserve_time is not None:
        if len(reserve_time) != 5:
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'time', None)

        hour, minute = reserve_time.split(':')
        hour = parse_int(hour)
        minute = parse_int(minute)
        if math.isnan(hour) or math.isnan(minute):
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'time', None)

        # if hour < 10 or hour > 16:
        #     # Outside of business hours
        #     return build_validation_result(False, 'time', 'Our business hours are from ten a m. to five p m. Can you specify a time during this range?')

    if email is not None:
    	if not isvalid_email(email):
    		return build_validation_result(False, 'email', 'I did not understand that, what is your email address?')

    return build_validation_result(True, None, None)


""" --- Functions that control the bot's behavior --- """


def make_reservations(intent_request):
    """
    Performs dialog management and fulfillment for ordering flowers.
    Beyond fulfillment, the implementation of this intent demonstrates the use of the elicitSlot dialog action
    in slot validation and re-prompting.
    """

    location = get_slots(intent_request)["location"]
    cuisine = get_slots(intent_request)['cuisine']
    num_people = get_slots(intent_request)["num_people"]
    date = get_slots(intent_request)["date"]
    reserve_time = get_slots(intent_request)["time"]
    email = get_slots(intent_request)["email"]
    source = intent_request['invocationSource']

    if source == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        slots = get_slots(intent_request)

        validation_result = validate_reservation(location, num_people, date, reserve_time, email)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])

        # Pass the price of the flowers back through session attributes to be used in various prompts defined
        # on the bot model.
        output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        # if flower_type is not None:
        #     output_session_attributes['Price'] = len(flower_type) * 5  # Elegant pricing model

        return delegate(output_session_attributes, get_slots(intent_request))

    # Order the flowers, and rely on the goodbye message of the bot to define the message to the end user.
    # In a real bot, this would likely involve a call to a backend service.
    
    if source == 'FulfillmentCodeHook':

        sqs_msg = ",".join([location, cuisine, date, reserve_time, num_people, email])
        response = sqs.send_message(
            QueueUrl=sqs_url,
            DelaySeconds=10,
            MessageAttributes={
                'Title': {
                    'DataType': 'String',
                    'StringValue': 'Bot msg'
                }
            },
            MessageBody=(
                sqs_msg
            )
        )

        print(response['MessageId'])

        return close(intent_request['sessionAttributes'],
                     'Fulfilled',
                     {'contentType': 'PlainText',
                      'content': ('Thanks, we are searching our database for the best reasturant openning '
                                 'at {} on {}. An email will be sent to your mailbox at {}. Bon Appétit!').format(reserve_time, date, email)
                     }
                    )


""" --- Intents --- """


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'diningSuggestion':
        return make_reservations(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')


""" --- Main handler --- """


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))

    return dispatch(event)

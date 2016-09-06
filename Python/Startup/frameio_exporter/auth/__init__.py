from urllib2 import Request, urlopen
import json
AUTH_MODE_OAUTH = 'user-google'
AUTH_MODE_EMAIL = 'user-non-google'
AUTH_MODE_SIGNUP = 'user-eligible'

def jsonheader():
    return {'Content-Type': 'application/json'}

# Authentication / initial mail check
def check_email_type(email_address):
    """
    :param email_address:
    :return: auth_mode string: {'user-google', 'user-non-google' or 'user-eligible'}

    Frame.io supports login via Google OAuth2 (google-user), or via non-google (username/password)
    Responses are: 'user-google', 'user-non-google' or 'user-eligible' (sign-up required)

    POST: https://api.frame.io/users/check_elegible
    """

    print "Testing for email: " + str(email_address)
    values = {"email": str(email_address)}
    request = Request('https://api.frame.io/users/check_elegible', data=json.dumps(values), headers=jsonheader())
    response_body = urlopen(request).read()

    print "Response body: " + str(response_body)

    response_json = json.loads(response_body)

    # Responses looks like this:
    # Gmail/Googlemail domain
    # {"messages":["Success"],"action_key":"user-google"}
    # Non Gamil/Googlemail domain
    # {"messages":["Success"],"action_key":"user-non-google"}
    # Email is eligible but it's not a Google Account
    # {"messages":["Success"],"action_key":"user-eligible","google_account":"false"}

    if response_json.has_key('errors'):
        print 'Email check failed: %s' % (response_json['errors'])
        return None
    elif response_json.has_key('action_key'):
        user_type = response_json['action_key']
        return user_type
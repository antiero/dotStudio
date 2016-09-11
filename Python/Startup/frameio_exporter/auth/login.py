# auth.login - objects for handling authentication with frame.io
from PySide.QtWebKit import QWebView
from PySide.QtCore import QObject, QUrl, Signal, Slot
import urllib2
import json
from urllib2 import Request, urlopen
from oauth2client.client import flow_from_clientsecrets
import httplib2
import logging
from frameio_exporter.auth import jsonheader

class FrameIOLoginHandler(QObject):

    # When Login is successful, pass a dict with frame.io credentials
    loggedInSignal = Signal(dict)

    def __init__(self, email):

        # The 'x' component
        self.frameio_user_id = None

        # The 'y' component
        self.frameio_token = None

        # The email address used for Frame.io login
        self.frameio_email = email

        # The Readable name of a User
        self.frameio_username = None

        self.authenticated = False


class BasicLoginHandler(FrameIOLoginHandler):
    
    # Signal to notify UI that a Password needs to be supplied
    passwordRequiredSignal = Signal()

    def __init__(self, email):
        """
        A Frame.io login handled via username and password method.
        """
        super(FrameIOLoginHandler, self).__init__()
        self.frameio_password = ""
        self.frameio_email = email

    def login(self):
        """
        Log in via Username-Password method. 
        Returns True if login successful, False otherwise.
        """
        print "Attempting login with password: " + str(self.frameio_password)
        if not self.frameio_email or not self.frameio_password:
            print "Both Email and password must be specified"
            self.passwordRequiredSignal.emit()
            return

        logging.info('Logging in as ' + self.frameio_email )
        values = {'a' : self.frameio_email , 'b' : self.frameio_password}
        request = Request('https://api.frame.io/login', data=json.dumps(values), headers=jsonheader())
        response_body = urlopen(request).read()

        print response_body

        logindata = json.loads(response_body)
        if logindata.has_key("errors"):
            logging.error("login: %s"%(logindata["errors"]))
            self.authenticated = False
            return [None, logindata["errors"]]

        logging.info( logindata['messages'][0]) 
        self.projectid = ''

        logging.info( "BasicLoginHandler login: logindata['x']: " + str(logindata['x']) )
        logging.info( "BasicLoginHandler login: logindata['y']: " + str(logindata['y']) )

        self.authenticated = True

        # Store the useful bits for obtaining data (user_id + token)
        self.frameio_user_id = logindata['x']
        self.frameio_token = logindata['y']

        # Emit a Logged in Signal, passing x-y frame.io creds
        self.loggedInSignal.emit({'user_id': self.frameio_user_id,
                                  'token'  : self.frameio_token}
                                )


class OAuthWebWidget(QWebView):

    # Signal we'll use when an authorisation code is received
    authCodeReceivedSignal = Signal(str)

    def __init__(self, authorize_url):
        """
        Custom Webview widget to handle authentication of an authorisation url.
        authorize_url is string returned via flow_from_clientsecrets.step1_get_authorize_url object

        If Authorization is successful, returns an access code required for step2 of oauth flow object
        """

        QWebView.__init__(self)
        self.URL = QUrl.fromPercentEncoding(str(authorize_url))
        self.setUrl(self.URL)

        self.titleChanged.connect(self.handleTitleChange)

        self.load(self.URL)

    def handleTitleChange(self, title):
        # The code We want to generate an oauth2 access token is contained in the title of the HTML page.
        # When the URL has changed, inspect the Title, and see if it contains a 'code=' fragment

        # A successful login should give something like: u'Success code=4/HyK1mzApexLDkplXcc4yj6NPWm3KxrxdsAPZWANJM**'
        if title.find("code=") != -1:
            self.access_code = title.split('Success code=')[-1]
            self.authCodeReceivedSignal.emit(self.access_code)
            return self.access_code

class OAuthLoginHandler(FrameIOLoginHandler):
    def __init__(self, email):

        """
        A Frame.io login handled via Google OAuth method.
        This method relies on user entering Google Account credentials via Webview
        """

        super(FrameIOLoginHandler, self).__init__()

        self.email = email

        # A flow_from_clientsecrets object
        self.oauth_flow = None

        # Retrieved from flow.step1_get_authorize_url() - a string that is converted to Qurl.fromPercentEncoiding
        self.oauth_authorize_url = "" # 
        
        # An expiring access code which is retrieved from the title bar during Google Authentication
        self.oauth_access_code = ""

        # Used for flow - step2_exchange(oauth_access_code)
        self.oauth_credentials = None

        # The webview widget presented for Google OAuth Session Authentication
        self.webviewWidget = QWebView()

    # A slot to handle the authorisation code when received
    @Slot(str)
    def on_access_code_received(self, code):
        print "SLOT received:" + str(code)
        self.oauth_access_code = code
        self.oauth_webview.close()
        self.handleOAuthFlowStep2()

    def prepareWebViewWidgetForGoogleLogin(self):
        f = "/workspace/dotStudio/Python/Startup/frameio_exporter/auth/client_secret.json"

        try:
            self.oauth_flow = flow_from_clientsecrets(f, scope='https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email',
                                   redirect_uri='urn:ietf:wg:oauth:2.0:oob')
        except:
            error = sys.exc_info()[0]
            logging.error("Unable to authenticate via OAuth flow object, error: " + str(error))
            return 

        authorize_url = self.oauth_flow.step1_get_authorize_url()

        # We can pre-populate the email field by appending login_hint
        authorize_url += '&login_hint=%s' % self.email

        self.oauth_webview = OAuthWebWidget(authorize_url)
        logging.info("Now showing Google WebView...")
        self.oauth_webview.show()

        self.oauth_webview.authCodeReceivedSignal.connect(self.on_access_code_received)

    def handleOAuthFlowStep2(self):
        if self.oauth_flow:
            self.oauth_credentials = self.oauth_flow.step2_exchange(self.oauth_access_code)
            self.http_auth = self.oauth_credentials.authorize(httplib2.Http())
            self.oauth_values = values = {"email": self.email, "access_token" : self.oauth_credentials.access_token}
            request = Request('https://api.frame.io/sessions/validate_token', data=json.dumps(values), headers=jsonheader())

            logging.info("Validating token with frame.io...")
            response_body = urlopen(request).read()

            response_json = json.loads(response_body)
            logging.info(str(response_json))

            # A successsful validation should resul in response should like this:
            # {"x":"XX84d854-f3d9-4a73-b31f-c6c304372ceb","y":"XXa8bbd5-1ac8-4c97-b121-3b2757827f14","messages":["Successfully logged in as Joe Blogs"]}
            # A failed login will have an "errors" key.

            if response_json.has_key("errors"):
                print "TODO: Handle Error with authentication here"
            elif response_json.has_key("messages"):
                print "Success message: " + str(response_json['messages'])
                self.frameio_user_id = response_json['x']
                self.frameio_token = response_json['y']

                # Emit a Logged in Signal, passing x-y frame.io creds
                self.loggedInSignal.emit({'user_id': self.frameio_user_id,
                                          'token'  : self.frameio_token}
                                        )
    
    def login(self):
        self.prepareWebViewWidgetForGoogleLogin()


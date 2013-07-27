import os
from flask import Flask, redirect, url_for, render_template, request, session
import redis
import unittest
from dbtools import DB
from dbsite import Site
from dbuser import User


app = Flask(__name__)
# secret key for session storage with cookies
# set SECRET_KEY environment variable in heroku to something SECRET
app.secret_key = os.environ.get('SECRET_KEY', 'development_fallback')
app.config['db'] = 0

def loggedin():
    return session.get('loggedin', None)

@app.route('/')
def root():
    '''
    Root page does one of several things
    - Home page for a logged-in user
    - Home page for a non-logged-in viewer
    - Redirect to root user creation if no users exist
    '''
    dbnumber=app.config['db']
    s = Site(dbnumber)
    s.start()
    if not User.getuserscount(dbnumber):
        return redirect(url_for('rootuser'))
    else:
        return render_template('index.html', name=s.name, user=loggedin())
        
@app.route('/createrootuser', methods=['GET','POST'])
def rootuser():
    '''
    rootuser page does one of several things
    - root userid/password entry for virgin system
    - root userid/password submit destination for virgin system
    '''
    dbnumber=app.config['db']
    s = Site(dbnumber)
    s.start()
    if not User.getuserscount(dbnumber): 
        if request.method == 'POST'and \
            request.form['password'] == request.form['passwordcheck']:
            ru = User(dbnumber)
            ru.setusername(request.form['username'])
            ru.setproperties(password=request.form['password'])
            ru.setlevel(User.LEVEL_ROOT)
            if not ru.isvalid:
                ru.remove()
            return redirect(url_for('root'))
        else:
            return render_template('rootuser.html', name=s.name, user=None)
    else:
        return redirect(url_for('root'))

@app.route('/login', methods=['POST','GET'])
def login():
    '''
    Used for login and logging out (if no username is passed)
    '''
    dbnumber=app.config['db']
    username = request.form.get('username', None)
    if request.method == 'POST':
        u = User(dbnumber, username = username)
        if u.isvalid and u.checkpassword(request.form['password']):
            session['loggedin'] = u.username
    else:
        session['loggedin'] = None
    return redirect(url_for('root'))

@app.route('/resetsystem')
def resetsystem():
    '''
    Clear the database entirely
    '''
    dbnumber=app.config['db']
    u = User(dbnumber, username = loggedin())
    if u.isvalid and u.level == User.LEVEL_ROOT:
        with DB(dbnumber) as db:
            db.reset()
    return redirect(url_for('root'))

#
# Unit Test 
#

class TestSequenceFunctions(unittest.TestCase):

    def setUp(self):
        app.config['db'] = DB.DBNTEST  # use testing database
        app.debug = True
        self.app = app.test_client()
        with DB(DB.DBNTEST) as db:
            db.reset()

    def tearDown(self):
        with DB(DB.DBNTEST) as db:
            db.reset()
        
    def test_rootempty(self):
        rv = self.app.get('/', follow_redirects=True)
        assert 'Please enter ROOT USER credentials' in rv.data
        rv = self.app.post('/createrootuser', 
            data=dict(username='',password='rootpass',passwordcheck='rootpass'), 
            follow_redirects=True)
        assert 'Please enter ROOT USER credentials' in rv.data  # create fail
        rv = self.app.post('/createrootuser', 
            data=dict(username='rootuser',password='rootpass',passwordcheck='rootpassx'), 
            follow_redirects=True)
        assert 'Please enter ROOT USER credentials' in rv.data  # create fail
        rv = self.app.post('/createrootuser', 
            data=dict(username='rootuser',password='rootpass',passwordcheck='rootpass'), 
            follow_redirects=True)
        assert 'Empty Page' in rv.data  # will have to change this!

    def test_login(self):
        rv = self.app.get('/', follow_redirects=True)
        rv = self.app.post('/createrootuser', 
            data=dict(username='rootuser',password='rootpass',passwordcheck='rootpass'), 
            follow_redirects=True)
        rv = self.app.post('/login', data=dict(username='nobody', password='nuthin'),
            follow_redirects=True)
        assert 'Sign in' in rv.data
        rv = self.app.post('/login', data=dict(username='rootuser', password='nuthin'),
            follow_redirects=True)
        assert 'Sign in' in rv.data
        rv = self.app.post('/login', data=dict(username='rootuser', password='rootpass'),
            follow_redirects=True)
        assert 'Sign in' not in rv.data
        rv = self.app.get('/login',follow_redirects=True)
        assert 'Sign in' in rv.data
        rv = self.app.get('/resetsystem', follow_redirects=True)  # can't reset if not logged in
        assert 'Please enter ROOT USER credentials' not in rv.data 
        rv = self.app.post('/login', data=dict(username='rootuser', password='rootpass'))
        rv = self.app.get('/resetsystem', follow_redirects=True)  # can't reset if not logged in
        assert 'Please enter ROOT USER credentials' in rv.data 

if __name__ == '__main__':
    unittest.main()


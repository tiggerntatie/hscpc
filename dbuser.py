import redis
import unittest
from dbtools import DB
from werkzeug.security import generate_password_hash, check_password_hash

class User(object):
    '''
    Class to represent a user in the site

    Each user/<uid> has 
        username-><string>, 
        email-><string>, 
        realname-><string>, 
        passwordhash-><string>
        level-><integer>        1 = root, 2 = admin, 3 = coach, 4 = contestant, 5 = visitor
        
    '''
    KEY_USER_UID = 'u/' # append uid
    HKEY_USERNAME = 'u'
    HKEY_EMAIL = 'e'
    HKEY_REALNAME = 'r'
    HKEY_PASSWORDHASH = 'p'
    HKEY_LEVEL = 'l'
    KEY_SITE_ADMINUIDS = 'site/adminuids'
    KEY_SITE_COACHUIDS = 'site/coachuids'
    KEY_SITE_CONTESTANTUIDS = 'site/contestantuids'
    KEY_SITE_USERNAMES = 'site/usernames'  # hash of username->uid
    KEY_SITE_EMAILS = 'site/emails'     # hash of email->uid
    KEY_SITE_CONTESTS = 'site/contests'
    
    LEVEL_ANY = 0
    LEVEL_ROOT = 1
    LEVEL_ADMIN = 2
    LEVEL_COACH = 3
    LEVEL_CONTESTANT = 4
    LEVEL_VISITOR = 5
    LEVEL_PENDING = 6
    LEVEL_STRINGS = {LEVEL_ROOT:'ROOT', 
        LEVEL_ADMIN:'Contest Administrator', 
        LEVEL_COACH:'Coach',
        LEVEL_CONTESTANT:'Contestant',
        LEVEL_VISITOR:'Visitor',
        LEVEL_PENDING:'Pending'}

    @classmethod
    def getusers(cls, dbnumber, **kwargs):
        levelspec = kwargs.get('levelspec', cls.LEVEL_ANY)
        with DB(dbnumber) as db:
            alluserkeys = cls._getallusers(db)
            alluserkeys = [key[len(cls.KEY_USER_UID):] for key in alluserkeys]
            users = [User(dbnumber, userid=key) for key in alluserkeys]
            users = [user for user in users 
                if levelspec == cls.LEVEL_ANY or user.level == levelspec]
            return users    
    
    @classmethod
    def getuserscount(cls, dbnumber):
        with DB(dbnumber) as db:
            return len(cls._getallusers(db))
    
    @classmethod
    def _getallusers(cls, db):
        return db.r.keys(cls.KEY_USER_UID + '*')
    
    def __init__(self, dbnumber, **kwargs):
        self.isvalid = False
        self.dbnumber = dbnumber
        self.username = kwargs.get('username', '')
        self.userid = kwargs.get('userid', '')
        self.email = kwargs.get('email', '')
        self.realname = ''
        self.passwordhash = ''
        self.level = self.LEVEL_PENDING
        with DB(self.dbnumber) as db:
            if not (self.username or self.userid or self.email):
                # Creating empty user from nothing
                self.userid = db.getuniqueid()
                self.key = self._userkey()
                self._createuser(db)
            else:
                if self.username:
                    self.userid = db.r.hget(self.KEY_SITE_USERNAMES, self.username)
                elif self.email: 
                    self.userid = db.r.hget(self.KEY_SITE_EMAILS, self.email)
                if self.userid:
                    self.key = self._userkey()
                    self._loaduser(db)
                    if self.username:
                        self.isvalid = True


    def setproperties(self, **kwargs):
        if kwargs.has_key('username'):
            self.setusername(kwargs['username'])
        if kwargs.has_key('email'):
            self.setemail(kwargs['email'])
        with DB(self.dbnumber) as db:
            self.realname = kwargs.get('realname', self.realname)
            if kwargs.has_key('password'):
                self.passwordhash = generate_password_hash(kwargs['password'])
            self._updateuser(db)

            
    def checkpassword(self, password):
        '''
        Return True if password hash matches stored.
        '''
        return check_password_hash(self.passwordhash, password)

    def usernameexists(self, username):
        with DB(self.dbnumber) as db:
            return self._usernameexists(db, username)
            
    def setusername(self, username):
        with DB(self.dbnumber) as db:
            if not self._usernameexists(db, username):
                db.r.hset(self.KEY_SITE_USERNAMES, username, self.userid)
                self.username = username
                if self.username:
                    self.isvalid = True
            
    def emailexists(self, email):
        with DB(self.dbnumber) as db:
            return self._emailexists(db, email)
            
    def setemail(self, email):
        with DB(self.dbnumber) as db:
            if not self._emailexists(db, email):
                db.r.hset(self.KEY_SITE_EMAILS, email, self.userid)
                self.email = email

    def levelstring(self):
        return self.LEVEL_STRINGS[self.level]
        
    def setlevel(self, level):
        assert level <= self.LEVEL_VISITOR and level >= self.LEVEL_ROOT
        self.level = level
        with DB(self.dbnumber) as db:
            self._updateuser(db)
                 
    def remove(self):
        '''
        Remove and clean up the uid 
        '''
        with DB(self.dbnumber) as db:
            if self.username:
                db.r.hdel(self.KEY_SITE_USERNAMES, (self.username))
            if self.email:
                db.r.hdel(self.KEY_SITE_EMAILS, (self.email))
            db.r.delete((self.key))
        
            
    def _usernameexists(self, db, username):
        return db.r.hexists(self.KEY_SITE_USERNAMES, username)
         
    def _emailexists(self, db, email):
        return db.r.hexists(self.KEY_SITE_EMAILS, email)

    def _userkey(self):
        return self.KEY_USER_UID + self.userid
        
    def _createuser(self, db):
        '''
        Create all data objects for new user object
        '''
        # user records in u/uid - users have no username or email yet
        self.username = self.email = self.realname = self.passwordhash = ''
        self._updateuser(db)
        
    def _updateuser(self, db):
        '''
        Store all attributes to user object
        '''
        db.r.hset(self.key, self.HKEY_USERNAME, self.username)
        db.r.hset(self.key, self.HKEY_EMAIL, self.email)
        db.r.hset(self.key, self.HKEY_REALNAME, self.realname)
        db.r.hset(self.key, self.HKEY_PASSWORDHASH, self.passwordhash)
        db.r.hset(self.key, self.HKEY_LEVEL, self.level)
        
    
    def _loaduser(self, db):
        '''
        Load the member variables from the data store, using uid as key
        '''
        data = db.r.hgetall(self.key)
        self.username = data[self.HKEY_USERNAME]
        self.email = data[self.HKEY_EMAIL]
        self.passwordhash = data[self.HKEY_PASSWORDHASH]
        self.realname = data[self.HKEY_REALNAME]
        self.level = int(data[self.HKEY_LEVEL])
        
        
        
class TestSequenceFunctions(unittest.TestCase):

    '''
    Every method named test_<name> will be executed as a unit test
    '''

    def setUp(self):
        pass

    def tearDown(self):
        with DB(DB.DBNTEST) as db:
            db.reset()
    
    def test_usercreateempty(self):
        s = User(DB.DBNTEST) # select DB 1 for testing
        self.assertEquals(s.username, '')
        self.assertNotEquals(s.userid, '')
        s2 = User(DB.DBNTEST, userid=s.userid)
        self.assertNotEqual(s, s2)
        self.assertEqual(s.userid, s2.userid)
        
    def test_usercreatenamed(self):
        s = User(DB.DBNTEST)
        s.setusername('fred')
        s2 = User(DB.DBNTEST, username='fred')
        self.assertEqual(s.userid, s2.userid)
        s3 = User(DB.DBNTEST, username='fred')
        self.assertEqual(s.userid, s3.userid)
        
    def test_usercreateemail(self):
        s = User(DB.DBNTEST)
        s.setusername('alice')
        s.setemail('alice@gmail.com')
        self.assertEqual('alice', s.username)
        self.assertEqual('alice@gmail.com', s.email)
        s2 = User(DB.DBNTEST, email='alice@gmail.com')
        self.assertEqual(s.userid, s2.userid)
        
    def test_usersetproperties(self):
        s = User(DB.DBNTEST)
        s.setproperties(username='alice', 
            email='alice@gmail.com', 
            realname='alice in wonderland',
            password='letmein')
        s2 = User(DB.DBNTEST, email='alice@gmail.com')
        self.assertEqual('alice in wonderland', s.realname)
        self.assertNotEqual('letmein', s.passwordhash)
        self.assertEqual(s2.realname, s.realname)
        self.assertEqual(s2.passwordhash, s.passwordhash)
        
    def test_userpasswords(self):
        s = User(DB.DBNTEST)
        s.setproperties(username='alice', 
            email='alice@gmail.com', 
            realname='alice in wonderland',
            password='letmein')
        self.assertEqual(s.username, 'alice')
        s2 = User(DB.DBNTEST, username='alice')
        self.assertTrue(s2.checkpassword('letmein'))
        self.assertFalse(s2.checkpassword('letmeinx'))

    def test_usermissing(self):
        s = User(DB.DBNTEST)
        s.setproperties(username='alice',
            email='alice@gmail.com',
            realname='alice in wonderland',
            password='letmein')
        self.assertEqual(s.username, 'alice')
        self.assertTrue(s.isvalid)
        s2 = User(DB.DBNTEST, email='fred@gmail.com')
        self.assertFalse(s2.isvalid)
        
    def test_remove(self):
        s = User(DB.DBNTEST)
        s.setproperties(username='alice',
            email='alice@gmail.com',
            realname='alice in wonderland',
            password='letmein')
        s.remove()
        s2 = User(DB.DBNTEST, username='alice')
        self.assertFalse(s2.isvalid)
        s3 = User(DB.DBNTEST, email='alice@gmail.com')
        self.assertFalse(s3.isvalid)
    
    def test_getusers(self):
        self.assertFalse(User.getuserscount(DB.DBNTEST))
        s = User(DB.DBNTEST)
        s.setproperties(username='alice',
            email='alice@gmail.com',
            realname='alice in wonderland',
            password='letmein')
        s2 = User(DB.DBNTEST)
        s2.setproperties(username='fred',
            email='fred@gmail.com',
            realname='fred in wonderland',
            password='letmeintoo')
        s3 = User(DB.DBNTEST)
        s3.setproperties(username='shrek',
            email='shrek@gmail.com',
            realname='shrek in wonderland',
            password='letmeinthree')
        s3.setlevel(User.LEVEL_CONTESTANT)
        allusers = User.getusers(DB.DBNTEST)
        self.assertEqual(len(allusers),3)
        cusers = User.getusers(DB.DBNTEST, levelspec=User.LEVEL_CONTESTANT)
        self.assertEqual(len(cusers),1)
        self.assertEqual(User.getuserscount(DB.DBNTEST), 3)
    

        
if __name__ == '__main__':
    unittest.main()


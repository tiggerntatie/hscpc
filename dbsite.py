import redis
import unittest
from dbtools import DB

class Site(object):
    '''
    Site object represents the entire data store for the web site. If no site
    data exist, then create default, empty data for the site and return. All
    public members will create/destroy database connection. All private
    members will accept a database connection reference as argument.
    
    Default site data include:
    
        root user id: site/rootuid -> 'uuid' or '' if none
        site name: site/name -> site name string
        contests: site/contests -> list of contest 'uuid'
        
        user info..        
        user info hashes: user/<uuid> -> hash of attributes
        admin user id list: site/adminuids -> list of 'uuid'
        coach user id list: site/coachuids -> list of 'uuid'
        contestant user id list: site/contestantuids -> list of 'uuid'
        alluser id list: site/alluids -> list of 'uuid'
        username hashes: site/usernames -> hash of username->uuid
        email hashes: site/emails -> hash of email->uuid
        
        
        contest info..
        contest info hashes: contest/<uuid> -> hash of attributes
        
        puzzle info..
        puzzle info hashes: puzzle/<uuid> -> hash of attributes
        
    '''
    
    KEY_SITE_NAME = 's/n'
    
    VALUE_SITE_DEFAULTNAME = 'HSCPC'
    
    def __init__(self, dbnumber):
        self.dbnumber = dbnumber
                
    def start(self):
        with DB(self.dbnumber) as db:
            if not self._exists(db):
                self._createdefault(db)
            self._loadsite(db)
                
    def _exists(self, db):
        return db.r.exists(self.KEY_SITE_NAME)
    
    def _createdefault(self, db):
        db.reset()
        db.r.set(self.KEY_SITE_NAME, self.VALUE_SITE_DEFAULTNAME)
        
    def _loadsite(self, db):
        self.name = db.r.get(self.KEY_SITE_NAME)
        
        
                
class TestSequenceFunctions(unittest.TestCase):

    '''
    Every method named test_<name> will be executed as a unit test
    '''

    def setUp(self):
        pass

    def tearDown(self):
        with DB(DB.DBNTEST) as db:
            db.reset()

    def test_sitecreate(self):
        s = Site(DB.DBNTEST) # select DB 1 for testing
        s.start()
        self.assertEquals(s.name, Site.VALUE_SITE_DEFAULTNAME)

        
if __name__ == '__main__':
    unittest.main()


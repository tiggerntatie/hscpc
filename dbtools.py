import os
import redis
import unittest
import uuid

class DB(object):
    '''
    Class to represent the database connection with Redis server. The member
    variable, r, points to the redis instance.
    '''
    DBN = 0
    DBNTEST = 1
    
    def __init__(self, dbnumber):
        self.dbnumber = dbnumber
        self.r = None
        pass
            
    def __enter__(self):
        redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
        self.r = redis.from_url(redis_url, self.dbnumber)
        return self
        
    def __exit__(self, type, value, traceback):
        self.r = None
        return
                    
    def reset(self):    
        '''
        Clear all data from the data store.
        '''
        self.r.flushdb()
        
    def getuniqueid(self):
        '''
        Return a unique identifier 
        '''
        return str(uuid.uuid1())
        



class TestSequenceFunctions(unittest.TestCase):

    '''
    Every method named test_<name> will be executed as a unit test
    '''

    def setUp(self):
        pass
    
    def tearDown(self):
        with DB(DB.DBNTEST) as db:
            db.reset()

    def test_dbconnect(self):
        with DB(DB.DBNTEST) as db:  # select DB 1 for testing
            db.r.set('test', 'value')
            result = db.r.get('test')
            self.assertEqual('value', result)
        
    def test_reset(self):
        with DB(DB.DBNTEST) as db:
            db.r.set('test', 'value')
            db.reset()
            result = db.r.get('test')
            self.assertIs(None, result)
            
    def test_uniqueid(self):
        with DB(DB.DBNTEST) as db:
            u1 = db.getuniqueid()
            u2 = db.getuniqueid()
            self.assertNotEqual(u1, u2)
            
            
if __name__ == '__main__':
    unittest.main()
        

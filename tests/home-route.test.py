import sys,pathlib,unittest,tempfile,json
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'system_integration'))
import home_route as h
class RouteTests(unittest.TestCase):
 def bus(self,initial,category=True):
  state={'defaultApps':dict(initial),'writes':[]}
  def call(uri,p):
   if uri==h.GET_SETTINGS:return {'returnValue':True,'settings':{'defaultApps':dict(state['defaultApps'])}}
   if uri.endswith('getAppInfo'):return {'returnValue':True,'appInfo':{'id':'test.home','appCategory':['home'] if category else None}}
   state['writes'].append((uri,p))
   if uri==h.SET_HOME:state['defaultApps']['home']=p['appId']
   if uri==h.SET_SETTINGS:state['defaultApps']=dict(p['settings']['defaultApps'])
   return {'returnValue':True}
  return state,call
 def test_exact_restore_absent_home_preserves_other_current_categories(self):
  state,bus=self.bus({'other':'a'});c={'app_id':'test.home','stock_home':'lg.home'};h.remember(c,bus);h.activate(c,bus)
  state['defaultApps']['new']='b';h.restore(c,bus)
  self.assertEqual(state['defaultApps'],{'other':'a','new':'b'})
 def test_restore_explicit_previous_home(self):
  state,bus=self.bus({'home':'previous.home'});c={'app_id':'test.home','stock_home':'lg.home'};h.remember(c,bus);h.activate(c,bus);h.restore(c,bus)
  self.assertEqual(state['defaultApps']['home'],'previous.home')
 def test_unregistered_category_does_not_write(self):
  state,bus=self.bus({},False);c={'app_id':'test.home','stock_home':'lg.home'};h.remember(c,bus)
  with self.assertRaises(RuntimeError):h.activate(c,bus)
  self.assertFalse(state['writes'])
 def test_independent_user_change_is_preserved(self):
  state,bus=self.bus({});c={'app_id':'test.home','stock_home':'lg.home'};h.remember(c,bus);h.activate(c,bus)
  state['defaultApps']['home']='different.home';h.restore(c,bus);self.assertEqual(state['defaultApps']['home'],'different.home')
if __name__=='__main__':unittest.main()

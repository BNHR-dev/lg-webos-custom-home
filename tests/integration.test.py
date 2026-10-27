import importlib.util
import pathlib
import tempfile
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'system_integration'))
spec = importlib.util.spec_from_file_location('engine', pathlib.Path(__file__).resolve().parents[1]/'system_integration/engine.py')
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)

class IntegrationTests(unittest.TestCase):
    def test_short_only_and_repeat(self):
        key = e.ShortHome(773)
        self.assertFalse(key.event('rcu', 773, 1, 1))
        self.assertFalse(key.event('rcu', 773, 2, 1.1))
        self.assertTrue(key.event('rcu', 773, 0, 1.2))
        self.assertFalse(key.event('rcu', 773, 0, 1.21))
        key.event('rcu', 773, 1, 2)
        self.assertFalse(key.event('rcu', 773, 0, 5))
        self.assertFalse(key.event('rcu', 103, 0, 6))

    def test_power_initial_reconnect_and_screen_saver(self):
        state = e.PowerTransitions()
        self.assertFalse(state.event('Active'))
        self.assertFalse(state.event('Active'))
        self.assertFalse(state.event('Screen Saver'))
        self.assertFalse(state.event('Active'))
        self.assertFalse(state.event('Suspend'))
        self.assertTrue(state.event('Active'))
        self.assertFalse(state.event('Active'))
        self.assertFalse(state.event('Active Standby'))
        self.assertTrue(state.event('Active'))

    def test_fragmented_and_pretty_json(self):
        stream = e.JSONStream()
        self.assertEqual(stream.feed(b'{"state":'), [])
        self.assertEqual(stream.feed(b'"Active"}\n{\n"state":"Suspend"\n}'),
                         [{'state':'Active'}, {'state':'Suspend'}])

    def test_no_focus_on_daemon_restart_and_home_disabled(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            e.write_json(root/'config.json', {'home':False, 'power':True})
            daemon = e.Daemon(root, root/'runtime')
            daemon.pending_home = {'due':0}
            daemon.refresh()
            self.assertIsNone(daemon.pending_home)
            self.assertIsNone(daemon.pending_power)
            daemon.select.close()

    def test_one_launch_then_no_retry_loop(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp); daemon=e.Daemon(root,root/'runtime')
            daemon.config={'app_id':'test.home','stock_home':'test.lg'}
            daemon.pending_home={'due':0,'until':1e20,'tries':0}
            with patch.object(e,'luna',side_effect=[{'appId':'test.lg'}, {'returnValue':True}]) as api:
                daemon.actions(); daemon.actions()
                self.assertEqual(api.call_count,2)
            self.assertIsNone(daemon.pending_home)
            daemon.select.close()

    def test_failed_home_launch_does_not_loop(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);daemon=e.Daemon(root,root/'runtime')
            daemon.config={'app_id':'test.home','stock_home':'test.lg'}
            daemon.pending_home={'due':0,'until':1e20,'tries':0}
            with patch.object(e,'luna',side_effect=[{'appId':'test.lg'}, {'returnValue':False,'errorText':'missing'}]) as api:
                daemon.actions();daemon.actions();self.assertEqual(api.call_count,2)
            self.assertIsNone(daemon.pending_home)
            daemon.select.close()


    def test_power_failure_is_bounded(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);daemon=e.Daemon(root,root/'runtime')
            daemon.config={'app_id':'test.home','stock_home':'test.lg'}
            daemon.power_state.previous='active'
            daemon.pending_power={'reason':'wake','due':0,'tries':0}
            def response(uri, payload):
                return {'appId':'test.video'} if uri.endswith('getForegroundAppInfo') else {'returnValue':False}
            with patch.object(e,'luna',side_effect=response) as api:
                for _ in range(8):
                    daemon.pending_power['due']=0; daemon.actions()
                self.assertEqual(api.call_count,16)
            self.assertIsNone(daemon.pending_power)
            daemon.select.close()

    def test_user_navigation_cancels_delayed_power_launch(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);daemon=e.Daemon(root,root/'runtime')
            daemon.config={'app_id':'test.home','stock_home':'test.lg'}
            daemon.power_state.previous='active'
            daemon.pending_power={'reason':'wake','due':0,'tries':1,'baseline':'test.video'}
            with patch.object(e,'luna',return_value={'appId':'test.other'}) as api:
                daemon.actions();self.assertEqual(api.call_count,1)
            self.assertIsNone(daemon.pending_power)
            daemon.select.close()

    def test_overlapping_launches_are_coalesced(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);daemon=e.Daemon(root,root/'runtime')
            daemon.config={'app_id':'test.home','stock_home':'test.lg'}
            with patch.object(e,'luna',return_value={'returnValue':True}) as api:
                self.assertTrue(daemon.launch('home'));self.assertTrue(daemon.launch('wake'))
                self.assertEqual(api.call_count,1)
            daemon.select.close()


    def test_only_one_boot_request_for_same_kernel_boot(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp)
            e.write_json(root/'config.json', {'home':False,'power':True})
            # A missing tmpfs marker denotes a new boot; wall-clock btime is not used.
            original_read=pathlib.Path.read_text
            def read(path,*args,**kwargs):
                if str(path)=='/proc/uptime':return '42.0 0.0'
                return original_read(path,*args,**kwargs)
            with patch.object(e,'boot_time',return_value='new-boot'), patch.object(pathlib.Path,'read_text',read):
                first=e.Daemon(root,root/'runtime',boot=True);first.refresh()
                self.assertEqual(first.pending_power['reason'],'boot')
                restarted=e.Daemon(root,root/'runtime',boot=True);restarted.refresh()
                self.assertIsNone(restarted.pending_power)
                first.select.close();restarted.select.close()

    def test_home_polling_never_redirects_video_without_lg_foreground(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);daemon=e.Daemon(root,root/'runtime')
            daemon.config={'app_id':'test.home','stock_home':'test.lg'}
            daemon.pending_home={'due':0,'until':1e20,'tries':0}
            with patch.object(e,'luna',return_value={'appId':'test.video'}) as api:
                for _ in range(21):
                    if daemon.pending_home:daemon.pending_home['due']=0
                    daemon.actions()
                self.assertTrue(all(c.args[0].endswith('getForegroundAppInfo') for c in api.call_args_list))
            self.assertIsNone(daemon.pending_home)
            daemon.select.close()

    def test_expired_home_does_not_launch_even_if_lg_event_arrives_late(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);daemon=e.Daemon(root,root/'runtime')
            daemon.config={'app_id':'test.home','stock_home':'test.lg'}
            daemon.pending_home={'due':0,'until':0,'tries':0}
            with patch.object(e,'luna',return_value={'appId':'test.lg'}) as api:
                daemon.actions();self.assertEqual(api.call_count,1)
            self.assertIsNone(daemon.pending_home)
            daemon.select.close()

    def test_native_lg_origin_qualifies_only_recent_stock_home(self):
        origin=e.NativeHomeOrigin('lg','ours')
        origin.event('video','foreground',1)
        self.assertFalse(origin.from_stock(2))
        origin.event('lg','foreground',3)
        self.assertTrue(origin.from_stock(3.1))
        origin.event('video','foreground',4)
        self.assertTrue(origin.from_stock(4.05))
        self.assertFalse(origin.from_stock(4.3))

    def test_native_duplicate_launch_is_suppressed(self):
        origin=e.NativeHomeOrigin('lg','ours')
        origin.event('lg','foreground',1)
        origin.event('ours','splash',2)
        self.assertFalse(origin.needed(1.9))
        origin.event('ours','foreground',3)
        self.assertFalse(origin.needed(4))

    def test_native_lg_short_home_launches_once_without_polling(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);daemon=e.Daemon(root,root/'runtime')
            daemon.config={'app_id':'ours','stock_home':'lg'}
            daemon.native_origin=e.NativeHomeOrigin('lg','ours')
            daemon.native_origin.event('lg','foreground',1)
            daemon.pending_home={'mode':'native-lg','down':2,'due':0,'until':1e20}
            with patch.object(e,'luna',return_value={'returnValue':True}) as api:
                daemon.actions();daemon.actions();self.assertEqual(api.call_count,1)
                self.assertTrue(api.call_args.args[0].endswith('/launch'))
            daemon.select.close()

    def test_native_lg_late_job_cannot_steal_focus(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);daemon=e.Daemon(root,root/'runtime')
            daemon.native_origin=e.NativeHomeOrigin('lg','ours')
            daemon.pending_home={'mode':'native-lg','down':2,'due':0,'until':0}
            with patch.object(e,'luna') as api:
                daemon.actions();api.assert_not_called()
            self.assertIsNone(daemon.pending_home)
            daemon.select.close()

if __name__=='__main__':unittest.main()

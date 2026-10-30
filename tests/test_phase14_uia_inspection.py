import json
import subprocess
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from contextlib import redirect_stdout
import io
from audition_controller import AuditionController as C


class UIAInspectionTests(unittest.TestCase):
    def setUp(self):
        self.c=C()
        vendor=patch('controller_modules.native_uia_inspection.Path.is_dir',return_value=True)
        vendor.start();self.addCleanup(vendor.stop)

    def test_snapshot_restricted_to_audition_pid(self):
        class Result:
            returncode=0;stderr=''
            stdout=json.dumps(dict(pid=42,actions_performed=False,windows=[],control_count=0))
        with patch.object(self.c,'_audition_pid',return_value=42),patch('controller_modules.native_uia_inspection.subprocess.run',return_value=Result()) as runner:
            result=self.c.inspect_audition_controls(title_contains='OMF')
        self.assertIn('42',runner.call_args.args[0]);self.assertFalse(result['actions_performed'])

    def test_mismatched_pid_rejected(self):
        class Result:
            returncode=0;stderr='';stdout=json.dumps(dict(pid=99,actions_performed=False,windows=[]))
        with patch.object(self.c,'_audition_pid',return_value=42),patch('controller_modules.native_uia_inspection.subprocess.run',return_value=Result()):
            with self.assertRaises(RuntimeError):self.c.inspect_audition_controls()

    def test_timeout_is_bounded(self):
        with patch.object(self.c,'_audition_pid',return_value=42),patch('controller_modules.native_uia_inspection.subprocess.run',side_effect=subprocess.TimeoutExpired('worker',1)):
            with self.assertRaises(TimeoutError):self.c.inspect_audition_controls(timeout=1)

    def test_invalid_limits_fail_before_host_lookup(self):
        with patch.object(self.c,'_audition_pid') as pid:
            with self.assertRaises(ValueError):self.c.inspect_audition_controls(max_controls=501)
        pid.assert_not_called()

    def test_worker_excludes_other_process_controls(self):
        from controller_modules import uia_worker
        rect=SimpleNamespace(left=0,top=0,right=10,bottom=10)
        class Control:
            def __init__(self,pid,name,children=()):
                self.element_info=SimpleNamespace(process_id=pid,name=name,control_type='Window',automation_id='',rectangle=rect)
                self.nodes=list(children)
            def children(self):return self.nodes
        root=Control(42,'Audition',[Control(99,'other process'),Control(42,'导出')])
        fake=SimpleNamespace(Desktop=lambda **kw:SimpleNamespace(windows=lambda **kwargs:[root]))
        output=io.StringIO()
        with patch.object(uia_worker.sys,'argv',['worker','42','10','3','Audition']), \
             patch.object(uia_worker.sys,'path',list(uia_worker.sys.path)), \
             patch.dict(uia_worker.sys.modules,{'pywinauto':fake}), \
             patch.object(uia_worker.os,'add_dll_directory') as dll, redirect_stdout(output):
            uia_worker.main()
        data=json.loads(output.getvalue())
        self.assertEqual(data['control_count'],2)
        self.assertEqual(data['windows'][0]['children'][0]['name'],'导出')
        self.assertFalse(data['actions_performed']);dll.return_value.close.assert_called_once()


if __name__=='__main__':unittest.main()

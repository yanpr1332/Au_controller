import unittest
from audition_controller import AuditionController as C


class SpectralGeometryTests(unittest.TestCase):
    def setUp(self):
        self.viewport=dict(left=10,top=20,width=101,height=101,time_start=0,time_end=10,frequency_min=100,frequency_max=10000,frequency_scale='log')

    def test_logarithmic_midpoint(self):
        result=C.plan_spectral_selection(viewport=self.viewport,tool='rectangle',points=[dict(seconds=0,hz=100),dict(seconds=5,hz=1000)])
        self.assertEqual(result['points'],[dict(x=10,y=120),dict(x=60,y=70)])
        self.assertFalse(result['native_action_executed'])

    def test_edges(self):
        result=C.plan_spectral_selection(viewport=self.viewport,tool='brush',points=[dict(seconds=0,hz=100),dict(seconds=10,hz=10000)])
        self.assertEqual(result['points'],[dict(x=10,y=120),dict(x=110,y=20)])

    def test_reject_out_of_viewport(self):
        with self.assertRaises(ValueError):C.plan_spectral_selection(viewport=self.viewport,tool='brush',points=[dict(seconds=0,hz=100),dict(seconds=11,hz=500)])

    def test_log_axis_rejects_zero(self):
        self.viewport['frequency_min']=0
        with self.assertRaises(ValueError):C.plan_spectral_selection(viewport=self.viewport,tool='brush',points=[dict(seconds=0,hz=0),dict(seconds=1,hz=500)])

    def test_linear_axis(self):
        self.viewport.update(frequency_scale='linear',frequency_min=0,frequency_max=10000)
        result=C.plan_spectral_selection(viewport=self.viewport,tool='brush',points=[dict(seconds=0,hz=0),dict(seconds=5,hz=5000)])
        self.assertEqual(result['points'][1],dict(x=60,y=70))


if __name__=='__main__':unittest.main()

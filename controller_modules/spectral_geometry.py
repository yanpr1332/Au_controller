"""Calibrated coordinate planning only; never controls Audition GUI."""
import math


class AuditionSpectralGeometry:
    @staticmethod
    def plan_spectral_selection(*,viewport,points,tool='lasso'):
        """Map seconds/Hz to window-relative pixels using supplied axis bounds.

        The viewport must come from a current, separately verified observation.
        This method neither captures the screen nor drives the mouse.
        """
        required={'left','top','width','height','time_start','time_end','frequency_min','frequency_max','frequency_scale'}
        if not isinstance(viewport,dict) or set(viewport)!=required:
            raise ValueError('Exact calibrated viewport fields required')
        if tool not in ('lasso','brush','rectangle'):raise ValueError('Unsupported spectral tool')
        def finite(value):
            return type(value) in (int,float) and math.isfinite(value)
        for name in required-{'frequency_scale'}:
            if not finite(viewport[name]):raise ValueError('Finite viewport coordinates required')
        left,top,width,height=(viewport[x] for x in ('left','top','width','height'))
        t0,t1,f0,f1=(viewport[x] for x in ('time_start','time_end','frequency_min','frequency_max'))
        scale=viewport['frequency_scale']
        if left<0 or top<0 or width<2 or height<2 or t0<0 or t1<=t0 or f0<0 or f1<=f0 or scale not in ('linear','log') or (scale=='log' and f0<=0):
            raise ValueError('Invalid viewport or frequency axis')
        minimum=2 if tool in ('brush','rectangle') else 3
        if not isinstance(points,list) or not minimum<=len(points)<=2048 or (tool=='rectangle' and len(points)!=2):
            raise ValueError('Invalid number of selection points')
        pixels=[]
        for point in points:
            if not isinstance(point,dict) or set(point)!={'seconds','hz'} or not finite(point['seconds']) or not finite(point['hz']):
                raise ValueError('Each point requires finite seconds and hz')
            seconds,hz=point['seconds'],point['hz']
            if not t0<=seconds<=t1 or not f0<=hz<=f1:raise ValueError('Point outside calibrated viewport')
            x=left+(seconds-t0)/(t1-t0)*(width-1)
            frequency_fraction=((math.log(hz)-math.log(f0))/(math.log(f1)-math.log(f0)) if scale=='log' else (hz-f0)/(f1-f0))
            y=top+(1-frequency_fraction)*(height-1)
            pixels.append(dict(x=round(x),y=round(y)))
        return dict(tool=tool,points=pixels,coordinate_space='window_relative',native_action_executed=False,
                    requires_current_screenshot_calibration=True)
